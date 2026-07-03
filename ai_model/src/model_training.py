#!/usr/bin/env python3
"""
RHD Heart Sound Classification Model
=====================================
A Mobile-First CNN for detecting Rheumatic Heart Disease from heart sound spectrograms.

Author: Your Research Team
Purpose: Clinical triage tool for resource-limited settings in Africa
Model: MobileNetV2 with transfer learning
Input: Mel Spectrograms (2D images) of heart sound segments
Output: 4-class severity grading (Grade 0-3)

References:
- PhysioNet 2016: Environmental noise robustness
- CirCOR Digiscope 2022: Clinical validation and pediatric data
"""


import os
import sys
import json
import pickle
import argparse
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration for the RHD classification model."""
    
    # Data paths
    DATA_PATH = os.environ.get('RHD_DATA_PATH', '../data/processed/heart_grades_classified')
    OUTPUT_PATH = os.environ.get('RHD_OUTPUT_PATH', '../exported_models')
    
    # Model architecture
    IMG_SIZE = (224, 224)  # MobileNetV2 standard input
    BATCH_SIZE = 32
    NUM_CLASSES = 4
    CLASS_NAMES = ['Grade_0', 'Grade_1', 'Grade_2', 'Grade_3']
    
    # Training parameters
    EPOCHS = 50
    INITIAL_LR = 0.001
    VALIDATION_SPLIT = 0.3  # 30% for validation+test
    TRAIN_SPLIT = 0.7  # 70% for training
    RANDOM_SEED = 42
    
    # Class weights (medical safety - prioritize severe cases)
    # Grading: Grade 3 (severe) gets highest weight
    # Rationale: Missing a sick child is a critical failure
    USE_BALANCED_WEIGHTS = True
    
    # Augmentation parameters
    AUGMENTATION = {
        'flip': True,
        'rotation': 0.15,
        'zoom': 0.15,
        'contrast': 0.1,
        'brightness': 0.1,
    }
    
    # Model export
    EXPORT_FORMATS = ['keras', 'tflite', 'saved_model']
    
    # Logging
    LOG_LEVEL = 'INFO'
    SAVE_HISTORY = True
    SAVE_PLOTS = True
    
    def __init__(self):
        # Create output directory
        os.makedirs(self.OUTPUT_PATH, exist_ok=True)
        os.makedirs(os.path.join(self.OUTPUT_PATH, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(self.OUTPUT_PATH, 'plots'), exist_ok=True)
        os.makedirs(os.path.join(self.OUTPUT_PATH, 'models'), exist_ok=True)
        
        # Set timestamp for this run
        self.TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.RUN_NAME = f"rhd_mobilenet_{self.TIMESTAMP}"


# ============================================================================
# DATA LOADING AND PREPROCESSING
# ============================================================================

class DataLoader:
    """Handles loading and preprocessing of heart sound spectrogram data."""
    
    def __init__(self, config):
        self.config = config
        self.class_names = None
        self.num_classes = None
        self.train_ds = None
        self.val_ds = None
        self.test_ds = None
        self.class_weights = None
        
    def load_data(self):
        """Load the spectrogram dataset from directory structure."""
        print("\n" + "="*60)
        print("📂 LOADING SPECTROGRAM DATASET")
        print("="*60)
        print(f"Data path: {self.config.DATA_PATH}")
        print(f"Image size: {self.config.IMG_SIZE}")
        print(f"Batch size: {self.config.BATCH_SIZE}")
        
        # Load full dataset with validation split
        # The 30% validation split will be further divided into val and test
        full_ds = tf.keras.preprocessing.image_dataset_from_directory(
            self.config.DATA_PATH,
            validation_split=self.config.VALIDATION_SPLIT,
            subset="training",  # Get the training portion first
            seed=self.config.RANDOM_SEED,
            image_size=self.config.IMG_SIZE,
            batch_size=self.config.BATCH_SIZE,
            label_mode='int',
            color_mode='rgb',
            shuffle=True
        )
        
        # Get class names from directory structure
        self.class_names = full_ds.class_names
        self.num_classes = len(self.class_names)
        print(f"\n📊 Classes found: {self.class_names}")
        print(f"   Number of classes: {self.num_classes}")
        
        # Get validation portion
        val_full_ds = tf.keras.preprocessing.image_dataset_from_directory(
            self.config.DATA_PATH,
            validation_split=self.config.VALIDATION_SPLIT,
            subset="validation",
            seed=self.config.RANDOM_SEED,
            image_size=self.config.IMG_SIZE,
            batch_size=self.config.BATCH_SIZE,
            label_mode='int',
            color_mode='rgb',
            shuffle=False
        )
        
        # Split the validation set into val and test (50/50 of the 30%)
        # This gives us 70% train, 15% val, 15% test
        full_ds_size = tf.data.experimental.cardinality(full_ds).numpy()
        val_full_size = tf.data.experimental.cardinality(val_full_ds).numpy()
        
        train_size = full_ds_size
        val_size = val_full_size // 2
        test_size = val_full_size - val_size
        
        print(f"\n📊 Dataset splits:")
        print(f"   Training: {train_size} batches")
        print(f"   Validation: {val_size} batches")
        print(f"   Test: {test_size} batches")
        
        # Split validation into val and test
        self.val_ds = val_full_ds.take(val_size)
        self.test_ds = val_full_ds.skip(val_size)
        self.train_ds = full_ds
        
        # Check class distribution
        self._check_class_distribution()
        
        # Calculate class weights for medical safety
        if self.config.USE_BALANCED_WEIGHTS:
            self._calculate_class_weights()
        
        return self.train_ds, self.val_ds, self.test_ds
    
    def _check_class_distribution(self):
        """Check and display class distribution in training set."""
        print("\n📊 Checking class distribution...")
        
        # Get labels from training set
        labels = []
        for _, y in self.train_ds:
            labels.extend(y.numpy().tolist())
        labels = np.array(labels)
        
        # Count per class
        class_counts = np.bincount(labels.astype(int))
        total = len(labels)
        
        print("   Training set distribution:")
        for i, (name, count) in enumerate(zip(self.class_names, class_counts)):
            percentage = (count / total) * 100
            bar = '█' * int(percentage / 2) + '░' * (50 - int(percentage / 2))
            print(f"   {name:12} : {count:6} ({percentage:5.1f}%) [{bar}]")
        
        # Check for imbalance
        min_count = class_counts.min()
        max_count = class_counts.max()
        imbalance_ratio = max_count / min_count
        
        if imbalance_ratio > 2:
            print(f"\n   ⚠️  Class imbalance detected! Ratio: {imbalance_ratio:.2f}:1")
            print("   → Using class weights to prioritize minority classes")
        else:
            print(f"\n   ✅ Dataset is relatively balanced")
        
        return class_counts
    
    def _calculate_class_weights(self):
        """
        Calculate class weights for medical safety.
        
        Rationale: In clinical triage, missing a severe case (Grade 3) 
        is a critical failure. We assign higher weights to severe grades 
        to prioritize recall (sensitivity).
        """
        print("\n⚖️  Calculating class weights (Medical Safety Priority)...")
        
        # Get training labels
        labels = []
        for _, y in self.train_ds:
            labels.extend(y.numpy().tolist())
        labels = np.array(labels)
        
        # Calculate balanced class weights
        classes = np.unique(labels)
        weights = class_weight.compute_class_weight(
            class_weight='balanced',
            classes=classes,
            y=labels
        )
        
        # Additional medical safety boost for severe grades
        # Grade 2 (moderate) gets 1.5x boost
        # Grade 3 (severe) gets 2.0x boost
        medical_boost = [1.0, 1.2, 1.5, 2.0]  # Grade 0, 1, 2, 3
        weights = weights * medical_boost[:len(classes)]
        
        # Normalize so weights sum to num_classes
        weights = weights / weights.mean()
        
        self.class_weights = dict(enumerate(weights))
        
        print("   Class Weights (higher = more important):")
        for i, (name, weight) in enumerate(zip(self.class_names, weights)):
            print(f"   {name:12} : {weight:.3f}")
            
        # Medical rationale
        print("\n   🏥 Clinical Rationale:")
        print("   → Grade 3 (Severe) gets highest weight")
        print("   → Grade 2 (Moderate) gets elevated weight")
        print("   → Grade 0 (Normal) gets lowest weight")
        print("   → This prioritizes Sensitivity (Recall) over Specificity")
        
        return self.class_weights


# ============================================================================
# DATA AUGMENTATION
# ============================================================================

def create_augmentation_pipeline(config):
    """
    Create data augmentation pipeline for training.
    
    Rationale: Heart sound spectrograms have natural variations due to:
    - Different stethoscope placements
    - Patient movement
    - Environmental noise
    - Varying chest sizes (pediatric vs adult)
    
    Augmentation helps the model learn robust features.
    """
    return models.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(config.AUGMENTATION['rotation']),
        layers.RandomZoom(config.AUGMENTATION['zoom']),
        layers.RandomContrast(config.AUGMENTATION['contrast']),
        layers.RandomBrightness(config.AUGMENTATION['brightness']),
    ])


def prepare_datasets(train_ds, val_ds, test_ds, config):
    """
    Prepare and optimize datasets for training.
    
    Uses .repeat() to prevent dataset exhaustion during training.
    """
    AUTOTUNE = tf.data.AUTOTUNE
    
    # Create augmentation pipeline
    augmentation = create_augmentation_pipeline(config)
    
    # Prepare training set (with augmentation)
    train_ds = train_ds.repeat()
    train_ds = train_ds.map(
        lambda x, y: (augmentation(x, training=True), y),
        num_parallel_calls=AUTOTUNE
    )
    train_ds = train_ds.shuffle(1000, seed=config.RANDOM_SEED)
    train_ds = train_ds.batch(config.BATCH_SIZE)
    train_ds = train_ds.prefetch(AUTOTUNE)
    
    # Prepare validation set (no augmentation)
    val_ds = val_ds.repeat()
    val_ds = val_ds.batch(config.BATCH_SIZE)
    val_ds = val_ds.prefetch(AUTOTUNE)
    
    # Prepare test set (no augmentation, no repeat)
    test_ds = test_ds.batch(config.BATCH_SIZE)
    test_ds = test_ds.prefetch(AUTOTUNE)
    
    # Calculate steps per epoch
    train_size = tf.data.experimental.cardinality(train_ds).numpy()
    val_size = tf.data.experimental.cardinality(val_ds).numpy()
    test_size = tf.data.experimental.cardinality(test_ds).numpy()
    
    # Use original dataset sizes for steps
    total_train = 0
    total_val = 0
    total_test = 0
    
    # Count actual samples
    for _, y in train_ds.take(1):
        total_train = len(y)
    for _, y in val_ds.take(1):
        total_val = len(y)
    for _, y in test_ds.take(1):
        total_test = len(y)
    
    steps_per_epoch = train_size * config.BATCH_SIZE // config.BATCH_SIZE
    validation_steps = val_size * config.BATCH_SIZE // config.BATCH_SIZE
    
    print(f"\n📊 Training steps: {steps_per_epoch}, Validation steps: {validation_steps}")
    
    return train_ds, val_ds, test_ds, steps_per_epoch, validation_steps


# ============================================================================
# MODEL ARCHITECTURE - MobileNetV2
# ============================================================================

def build_model(num_classes, img_size, learning_rate=0.001):
    """
    Build the MobileNetV2-based model for RHD classification.
    
    Rationale:
    1. Mobile-First: Designed for deployment on smartphones/microcontrollers
    2. Transfer Learning: Leverages pre-trained visual features
    3. Lightweight: Small memory footprint for resource-limited settings
    4. Proven: State-of-the-art on medical image classification tasks
    """
    print("\n🔨 BUILDING MOBILENETV2 MODEL")
    print("="*60)
    print("Architecture: MobileNetV2 (Mobile-First CNN)")
    print("Rationale: Deployable in resource-limited African clinics")
    print("Transfer Learning: Pre-trained on ImageNet")
    
    # Load base model with pre-trained weights
    base_model = tf.keras.applications.MobileNetV2(
        include_top=False,
        weights='imagenet',
        input_shape=(*img_size, 3)
    )
    
    # Freeze base model initially
    base_model.trainable = False
    
    print(f"Base model: {base_model.name}")
    print(f"Total parameters: {base_model.count_params():,}")
    print("Initial state: Frozen (transfer learning)")
    
    # Build the complete model
    model = models.Sequential([
        # Input layer
        layers.Input(shape=(*img_size, 3)),
        
        # Preprocessing (MobileNetV2 expects values in [-1, 1])
        layers.Rescaling(1./127.5, offset=-1),
        
        # Base model
        base_model,
        
        # Global pooling (reduces spatial dimensions to 1x1)
        layers.GlobalAveragePooling2D(),
        
        # Dense layers for classification
        layers.Dense(256, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.5),
        
        layers.Dense(128, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        
        # Output layer with softmax for multi-class classification
        layers.Dense(num_classes, activation='softmax')
    ])
    
    # Compile model
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='sparse_categorical_crossentropy',
        metrics=[
            'accuracy',
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=2, name='top_2_accuracy')
        ]
    )
    
    print("\n📊 Model Summary:")
    model.summary()
    
    return model, base_model


# ============================================================================
# TRAINING CALLBACKS
# ============================================================================

def create_callbacks(config):
    """Create training callbacks for optimal learning and monitoring."""
    
    callbacks = []
    
    # 1. Model Checkpoint - Save best model
    checkpoint_path = os.path.join(
        config.OUTPUT_PATH, 'models',
        f"{config.RUN_NAME}_best.keras"
    )
    callbacks.append(
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint_path,
            monitor='val_accuracy',
            save_best_only=True,
            mode='max',
            verbose=1
        )
    )
    
    # 2. Early Stopping - Prevent overfitting
    callbacks.append(
        tf.keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=7,
            restore_best_weights=True,
            mode='max',
            verbose=1
        )
    )
    
    # 3. Reduce Learning Rate - When plateau
    callbacks.append(
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=1e-7,
            verbose=1
        )
    )
    
    # 4. Learning Rate Scheduler - Cosine decay
    def cosine_decay(epoch):
        initial_lr = config.INITIAL_LR
        total_epochs = config.EPOCHS
        decay = 0.5 * (1 + np.cos(np.pi * epoch / total_epochs))
        return initial_lr * decay
    
    callbacks.append(
        tf.keras.callbacks.LearningRateScheduler(
            cosine_decay,
            verbose=0
        )
    )
    
    print("\n📋 Callbacks configured:")
    print(f"   ✓ Model Checkpoint (best val_accuracy)")
    print(f"   ✓ Early Stopping (patience=7)")
    print(f"   ✓ Reduce LR (factor=0.5, patience=3)")
    print(f"   ✓ Cosine Decay Learning Rate")
    
    return callbacks


# ============================================================================
# FINE-TUNING
# ============================================================================

def fine_tune_model(model, base_model, train_ds, val_ds, config):
    """
    Unfreeze the top layers of the base model for fine-tuning.
    
    Rationale: After initial training with frozen base, we unfreeze
    the top layers to adapt the pre-trained features to our specific
    heart sound spectrogram patterns.
    """
    print("\n🔧 FINE-TUNING PHASE")
    print("="*60)
    
    # Unfreeze the top layers of the base model
    base_model.trainable = True
    
    # Freeze the first 100 layers (keeps low-level features)
    for layer in base_model.layers[:100]:
        layer.trainable = False
    
    print(f"Fine-tuning: {base_model.trainable} layers")
    print(f"Frozen: First 100 layers (low-level features)")
    print(f"Trainable: Remaining {len(base_model.layers) - 100} layers")
    
    # Re-compile with lower learning rate
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config.INITIAL_LR / 10),
        loss='sparse_categorical_crossentropy',
        metrics=[
            'accuracy',
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=2, name='top_2_accuracy')
        ]
    )
    
    # Train for a few more epochs
    print("\n🚀 Starting fine-tuning...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=10,
        steps_per_epoch=config.train_steps,
        validation_steps=config.val_steps,
        callbacks=create_callbacks(config),
        verbose=1
    )
    
    return model, history


# ============================================================================
# EVALUATION
# ============================================================================

def evaluate_model(model, test_ds, class_names, config):
    """Comprehensive evaluation of the trained model."""
    
    print("\n📊 MODEL EVALUATION")
    print("="*60)
    
    # 1. Basic evaluation
    test_loss, test_acc, test_top2 = model.evaluate(test_ds, verbose=1)
    print(f"\n📈 Test Results:")
    print(f"   Loss: {test_loss:.4f}")
    print(f"   Accuracy: {test_acc:.4f}")
    print(f"   Top-2 Accuracy: {test_top2:.4f}")
    
    # 2. Predictions for classification report
    print("\n📋 Generating predictions...")
    y_true = []
    y_pred = []
    y_pred_probs = []
    
    for images, labels in test_ds:
        predictions = model.predict(images, verbose=0)
        y_true.extend(labels.numpy())
        y_pred.extend(np.argmax(predictions, axis=1))
        y_pred_probs.extend(predictions)
    
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_pred_probs = np.array(y_pred_probs)
    
    # 3. Classification report
    print("\n📋 Classification Report:")
    report = classification_report(
        y_true, 
        y_pred, 
        target_names=class_names,
        digits=4,
        output_dict=True
    )
    print(classification_report(
        y_true, 
        y_pred, 
        target_names=class_names,
        digits=4
    ))
    
    # 4. Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm, 
        annot=True, 
        fmt='d', 
        cmap='Blues',
        xticklabels=class_names,
        yticklabels=class_names
    )
    plt.title('Confusion Matrix - RHD Classification', fontsize=14)
    plt.xlabel('Predicted Grade', fontsize=12)
    plt.ylabel('True Grade', fontsize=12)
    plt.tight_layout()
    
    cm_path = os.path.join(config.OUTPUT_PATH, 'plots', f"{config.RUN_NAME}_confusion_matrix.png")
    plt.savefig(cm_path, dpi=300)
    print(f"\n✅ Confusion matrix saved: {cm_path}")
    plt.show()
    
    # 5. Calculate clinical metrics
    print("\n🏥 Clinical Performance Metrics:")
    
    for i, class_name in enumerate(class_names):
        # Sensitivity (Recall) - How well we detect each grade
        true_pos = cm[i, i]
        false_neg = np.sum(cm[i, :]) - true_pos
        sensitivity = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
        
        # Precision - How reliable is the prediction
        false_pos = np.sum(cm[:, i]) - true_pos
        precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
        
        print(f"\n   {class_name}:")
        print(f"   → Sensitivity (Recall): {sensitivity:.4f}")
        print(f"   → Precision: {precision:.4f}")
        print(f"   → F1-Score: {report[class_name]['f1-score']:.4f}")
    
    # 6. Save results
    results = {
        'test_loss': float(test_loss),
        'test_accuracy': float(test_acc),
        'test_top2_accuracy': float(test_top2),
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'timestamp': config.TIMESTAMP,
        'model_name': config.RUN_NAME
    }
    
    results_path = os.path.join(
        config.OUTPUT_PATH, 'logs',
        f"{config.RUN_NAME}_results.json"
    )
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results saved: {results_path}")
    
    return results, y_true, y_pred, y_pred_probs


# ============================================================================
# MODEL EXPORT
# ============================================================================

def export_models(model, config):
    """Export model in various formats for deployment."""
    
    print("\n💾 EXPORTING MODELS")
    print("="*60)
    
    exported_files = []
    
    # 1. Keras format
    keras_path = os.path.join(
        config.OUTPUT_PATH, 'models',
        f"{config.RUN_NAME}.keras"
    )
    model.save(keras_path)
    exported_files.append(keras_path)
    print(f"✓ Keras model: {keras_path}")
    
    # 2. SavedModel format (for TFServing)
    saved_model_path = os.path.join(
        config.OUTPUT_PATH, 'models',
        f"{config.RUN_NAME}_saved_model"
    )
    model.export(saved_model_path)
    exported_files.append(saved_model_path)
    print(f"✓ SavedModel: {saved_model_path}")
    
    # 3. TFLite format (for mobile deployment)
    try:
        # Convert to TFLite
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        # Optional: Quantization for smaller size
        # converter.target_spec.supported_types = [tf.float16]
        
        tflite_model = converter.convert()
        
        tflite_path = os.path.join(
            config.OUTPUT_PATH, 'models',
            f"{config.RUN_NAME}.tflite"
        )
        with open(tflite_path, 'wb') as f:
            f.write(tflite_model)
        exported_files.append(tflite_path)
        
        file_size = os.path.getsize(tflite_path) / (1024 * 1024)
        print(f"✓ TFLite model: {tflite_path} ({file_size:.2f} MB)")
        
        # Verify TFLite model
        interpreter = tf.lite.Interpreter(model_path=tflite_path)
        interpreter.allocate_tensors()
        print(f"  → TFLite input shape: {interpreter.get_input_details()[0]['shape']}")
        print(f"  → TFLite output shape: {interpreter.get_output_details()[0]['shape']}")
        
    except Exception as e:
        print(f"⚠️  TFLite export failed: {e}")
    
    return exported_files


# ============================================================================
# MAIN TRAINING PIPELINE
# ============================================================================

def main():
    """Main training pipeline for RHD classification model."""
    
    print("\n" + "="*70)
    print("❤️  RHD HEART SOUND CLASSIFICATION MODEL")
    print("="*70)
    print("Medical Triage Tool for Resource-Limited Settings")
    print("MobileNetV2-based Classification of Heart Sound Spectrograms")
    print("="*70)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Train RHD classification model')
    parser.add_argument('--data_path', type=str, default=None,
                       help='Path to spectrogram dataset')
    parser.add_argument('--output_path', type=str, default=None,
                       help='Path to save models and logs')
    parser.add_argument('--epochs', type=int, default=50,
                       help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Batch size for training')
    parser.add_argument('--fine_tune', action='store_true',
                       help='Enable fine-tuning phase')
    args = parser.parse_args()
    
    # Initialize configuration
    config = Config()
    if args.data_path:
        config.DATA_PATH = args.data_path
    if args.output_path:
        config.OUTPUT_PATH = args.output_path
    if args.epochs:
        config.EPOCHS = args.epochs
    if args.batch_size:
        config.BATCH_SIZE = args.batch_size
    
    print(f"\n📋 Configuration:")
    print(f"   Data path: {config.DATA_PATH}")
    print(f"   Output path: {config.OUTPUT_PATH}")
    print(f"   Epochs: {config.EPOCHS}")
    print(f"   Batch size: {config.BATCH_SIZE}")
    print(f"   Fine-tuning: {args.fine_tune}")
    
    # ======================================================================
    # Step 1: Load Data
    # ======================================================================
    loader = DataLoader(config)
    train_ds, val_ds, test_ds = loader.load_data()
    class_names = loader.class_names
    num_classes = loader.num_classes
    class_weights = loader.class_weights
    
    # ======================================================================
    # Step 2: Prepare Datasets
    # ======================================================================
    print("\n🔄 Preparing datasets for training...")
    train_ds, val_ds, test_ds, steps_per_epoch, validation_steps = prepare_datasets(
        train_ds, val_ds, test_ds, config
    )
    
    # Store for use in callbacks
    config.train_steps = steps_per_epoch
    config.val_steps = validation_steps
    
    # ======================================================================
    # Step 3: Build Model
    # ======================================================================
    model, base_model = build_model(
        num_classes, 
        config.IMG_SIZE,
        config.INITIAL_LR
    )
    
    # ======================================================================
    # Step 4: Train Model
    # ======================================================================
    print("\n🚀 STARTING TRAINING PHASE")
    print("="*60)
    print(f"Epochs: {config.EPOCHS}")
    print(f"Steps per epoch: {steps_per_epoch}")
    print(f"Class weights: {class_weights}")
    
    callbacks = create_callbacks(config)
    
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=config.EPOCHS,
        steps_per_epoch=steps_per_epoch,
        validation_steps=validation_steps,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1
    )
    
    # ======================================================================
    # Step 5: Fine-tune (Optional)
    # ======================================================================
    if args.fine_tune:
        model, fine_tune_history = fine_tune_model(
            model, base_model, train_ds, val_ds, config
        )
        
        # Combine histories
        for key in history.history:
            history.history[key].extend(fine_tune_history.history[key])
    
    # ======================================================================
    # Step 6: Evaluate Model
    # ======================================================================
    results, y_true, y_pred, y_pred_probs = evaluate_model(
        model, test_ds, class_names, config
    )
    
    # ======================================================================
    # Step 7: Export Models
    # ======================================================================
    exported_files = export_models(model, config)
    
    # ======================================================================
    # Step 8: Save Training History
    # ======================================================================
    if config.SAVE_HISTORY:
        history_path = os.path.join(
            config.OUTPUT_PATH, 'logs',
            f"{config.RUN_NAME}_history.pkl"
        )
        with open(history_path, 'wb') as f:
            pickle.dump(history.history, f)
        print(f"✓ Training history saved: {history_path}")
    
    # ======================================================================
    # Step 9: Final Report
    # ======================================================================
    print("\n" + "="*70)
    print("✅ TRAINING COMPLETE!")
    print("="*70)
    print(f"Run: {config.RUN_NAME}")
    print(f"Test Accuracy: {results['test_accuracy']:.4f}")
    print(f"Test Top-2 Accuracy: {results['test_top2_accuracy']:.4f}")
    print(f"Model saved to: {config.OUTPUT_PATH}/models/")
    print("="*70)
    
    return model, history, results


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        model, history, results = main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)