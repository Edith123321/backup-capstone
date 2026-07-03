// frontend_mobile/src/screens/PredictionScreen.js
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Share,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

export default function PredictionScreen({ route, navigation }) {
  const { result, fileName } = route.params;

  const isNormal = result.prediction === 'Normal';

  const handleShare = async () => {
    try {
      await Share.share({
        message: `Heart Sound Analysis Result:\n\nPrediction: ${result.prediction}\nConfidence: ${result.confidence.toFixed(1)}%\nNormal: ${(result.probabilities.Normal * 100).toFixed(1)}%\nRHD: ${(result.probabilities.RHD * 100).toFixed(1)}%`,
        title: 'Heart Sound Analysis Result',
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.fileName}>📄 {fileName}</Text>
      </View>

      <View style={[styles.resultCard, isNormal ? styles.normal : styles.rhd]}>
        <Text style={styles.predictionLabel}>Prediction</Text>
        <Text style={styles.predictionValue}>{result.prediction}</Text>
        <Text style={styles.confidenceValue}>
          {result.confidence.toFixed(1)}% Confidence
        </Text>
        <View style={styles.badgeContainer}>
          <View style={[styles.badge, isNormal ? styles.badgeNormal : styles.badgeRhd]}>
            <Text style={styles.badgeText}>
              {isNormal ? '✅ Healthy' : '⚠️ RHD Detected'}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>📊 Probabilities</Text>
        
        <View style={styles.probBar}>
          <View style={styles.probLabelContainer}>
            <Text style={styles.probLabel}>Normal</Text>
            <Text style={styles.probValue}>
              {(result.probabilities.Normal * 100).toFixed(1)}%
            </Text>
          </View>
          <View style={styles.probBarContainer}>
            <View 
              style={[
                styles.probBarFill, 
                styles.normalBar,
                { width: `${result.probabilities.Normal * 100}%` }
              ]} 
            />
          </View>
        </View>

        <View style={styles.probBar}>
          <View style={styles.probLabelContainer}>
            <Text style={styles.probLabel}>RHD</Text>
            <Text style={styles.probValue}>
              {(result.probabilities.RHD * 100).toFixed(1)}%
            </Text>
          </View>
          <View style={styles.probBarContainer}>
            <View 
              style={[
                styles.probBarFill, 
                styles.rhdBar,
                { width: `${result.probabilities.RHD * 100}%` }
              ]} 
            />
          </View>
        </View>
      </View>

      {result.visualization && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📊 Visualization</Text>
          <Image 
            source={{ uri: `data:image/png;base64,${result.visualization}` }}
            style={styles.visualization}
            resizeMode="contain"
          />
        </View>
      )}

      {result.top_features && result.top_features.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🔍 Key Features</Text>
          {result.top_features.slice(0, 5).map((feature, index) => (
            <View key={index} style={styles.featureItem}>
              <Text style={styles.featureName}>{feature.Feature}</Text>
              <Text style={styles.featureValue}>
                {(feature.Importance * 100).toFixed(2)}%
              </Text>
            </View>
          ))}
        </View>
      )}

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.shareButton} onPress={handleShare}>
          <Icon name="share-outline" size={24} color="#fff" />
          <Text style={styles.buttonText}>Share Results</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={styles.newButton}
          onPress={() => navigation.navigate('Home')}
        >
          <Icon name="refresh-outline" size={24} color="#667eea" />
          <Text style={styles.newButtonText}>New Analysis</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7fafc',
  },
  header: {
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  fileName: {
    fontSize: 16,
    color: '#4a5568',
  },
  resultCard: {
    margin: 16,
    padding: 24,
    borderRadius: 12,
    alignItems: 'center',
  },
  normal: {
    backgroundColor: '#c6f6d5',
  },
  rhd: {
    backgroundColor: '#fed7d7',
  },
  predictionLabel: {
    fontSize: 14,
    color: '#4a5568',
  },
  predictionValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#2d3748',
    marginTop: 4,
  },
  confidenceValue: {
    fontSize: 16,
    color: '#718096',
    marginTop: 4,
  },
  badgeContainer: {
    marginTop: 12,
  },
  badge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },
  badgeNormal: {
    backgroundColor: '#48bb78',
  },
  badgeRhd: {
    backgroundColor: '#fc8181',
  },
  badgeText: {
    color: '#fff',
    fontWeight: '600',
  },
  card: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2d3748',
    marginBottom: 12,
  },
  probBar: {
    marginBottom: 12,
  },
  probLabelContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  probLabel: {
    fontSize: 14,
    color: '#4a5568',
  },
  probValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2d3748',
  },
  probBarContainer: {
    height: 8,
    backgroundColor: '#e2e8f0',
    borderRadius: 4,
    overflow: 'hidden',
  },
  probBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  normalBar: {
    backgroundColor: '#48bb78',
  },
  rhdBar: {
    backgroundColor: '#fc8181',
  },
  visualization: {
    width: '100%',
    height: 300,
    borderRadius: 8,
  },
  featureItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#f7fafc',
  },
  featureName: {
    fontSize: 14,
    color: '#4a5568',
  },
  featureValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2d3748',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 16,
    gap: 12,
  },
  shareButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#667eea',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  newButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#667eea',
    gap: 8,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  newButtonText: {
    color: '#667eea',
    fontWeight: '600',
  },
});