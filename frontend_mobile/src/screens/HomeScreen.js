// frontend_mobile/src/screens/HomeScreen.js
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { Audio } from 'expo-av';
import Icon from 'react-native-vector-icons/Ionicons';

import { predictHeartSound } from '../services/api';
import { formatFileSize } from '../utils/helpers';

export default function HomeScreen({ navigation }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [recording, setRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);

  const handleFilePick = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['audio/*'],
        copyToCacheDirectory: true,
      });

      if (result.type === 'success') {
        setSelectedFile(result);
        setFileName(result.name);
        setFileSize(formatFileSize(result.size));
      }
    } catch (error) {
      console.error('Error picking file:', error);
      Alert.alert('Error', 'Failed to pick audio file');
    }
  };

  const startRecording = async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (permission.status !== 'granted') {
        Alert.alert('Permission required', 'Please grant microphone permission');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(recording);
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      Alert.alert('Error', 'Failed to start recording');
    }
  };

  const stopRecording = async () => {
    try {
      if (!recording) return;

      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      
      // Create a file object from the recording
      setSelectedFile({
        uri: uri,
        name: 'recording.wav',
        size: 0,
      });
      setFileName('Recording');
      setFileSize('Unknown');

      setRecording(null);
    } catch (error) {
      console.error('Error stopping recording:', error);
      Alert.alert('Error', 'Failed to stop recording');
    }
  };

  const handlePredict = async () => {
    if (!selectedFile) {
      Alert.alert('No File', 'Please select or record an audio file first');
      return;
    }

    setIsLoading(true);

    try {
      const result = await predictHeartSound(selectedFile);
      navigation.navigate('Prediction', { result, fileName });
    } catch (error) {
      console.error('Prediction error:', error);
      Alert.alert('Error', 'Failed to analyze heart sound. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🫀 Heart Sound Analysis</Text>
        <Text style={styles.subtitle}>Upload or record a heart sound for RHD detection</Text>
      </View>

      {/* Upload Section */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📤 Upload Audio</Text>
        <TouchableOpacity style={styles.uploadButton} onPress={handleFilePick}>
          <Icon name="cloud-upload-outline" size={40} color="#667eea" />
          <Text style={styles.uploadText}>Select Audio File</Text>
          <Text style={styles.uploadSubtext}>WAV, MP3, FLAC, M4A</Text>
        </TouchableOpacity>

        {fileName && (
          <View style={styles.fileInfo}>
            <Icon name="document-text-outline" size={24} color="#4a5568" />
            <View style={styles.fileDetails}>
              <Text style={styles.fileName}>{fileName}</Text>
              <Text style={styles.fileSize}>{fileSize}</Text>
            </View>
          </View>
        )}
      </View>

      {/* Recording Section */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🎙️ Record Sound</Text>
        <TouchableOpacity
          style={[styles.recordButton, isRecording && styles.recording]}
          onPress={isRecording ? stopRecording : startRecording}
        >
          <Icon 
            name={isRecording ? 'stop-circle' : 'mic-circle'} 
            size={60} 
            color={isRecording ? '#e53e3e' : '#667eea'} 
          />
          <Text style={styles.recordText}>
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </Text>
        </TouchableOpacity>
        <Text style={styles.recordHint}>
          {isRecording ? '🔴 Recording...' : 'Tap to record heart sound'}
        </Text>
      </View>

      {/* Predict Button */}
      <TouchableOpacity
        style={[styles.predictButton, (!selectedFile || isLoading) && styles.disabled]}
        onPress={handlePredict}
        disabled={!selectedFile || isLoading}
      >
        {isLoading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Icon name="analytics-outline" size={24} color="#fff" />
            <Text style={styles.predictText}>Analyze Heart Sound</Text>
          </>
        )}
      </TouchableOpacity>

      {/* Info Section */}
      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>ℹ️ About</Text>
        <Text style={styles.infoText}>
          This app uses a Random Forest model trained on 4000+ heart sound recordings
          to detect Rheumatic Heart Disease (RHD) from mitral valve sounds with 98.4% accuracy.
        </Text>
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
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2d3748',
  },
  subtitle: {
    fontSize: 14,
    color: '#718096',
    textAlign: 'center',
    marginTop: 4,
  },
  card: {
    backgroundColor: '#fff',
    marginHorizontal: 20,
    marginVertical: 10,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2d3748',
    marginBottom: 16,
  },
  uploadButton: {
    borderWidth: 2,
    borderColor: '#e2e8f0',
    borderStyle: 'dashed',
    borderRadius: 8,
    padding: 30,
    alignItems: 'center',
  },
  uploadText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4a5568',
    marginTop: 8,
  },
  uploadSubtext: {
    fontSize: 12,
    color: '#a0aec0',
    marginTop: 4,
  },
  fileInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f7fafc',
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
  },
  fileDetails: {
    marginLeft: 12,
    flex: 1,
  },
  fileName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2d3748',
  },
  fileSize: {
    fontSize: 12,
    color: '#718096',
  },
  recordButton: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  recording: {
    opacity: 0.7,
  },
  recordText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4a5568',
    marginTop: 8,
  },
  recordHint: {
    textAlign: 'center',
    fontSize: 14,
    color: '#718096',
    marginTop: 8,
  },
  predictButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#667eea',
    marginHorizontal: 20,
    marginVertical: 16,
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  disabled: {
    opacity: 0.5,
  },
  predictText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  infoCard: {
    backgroundColor: '#edf2f7',
    marginHorizontal: 20,
    marginVertical: 10,
    padding: 16,
    borderRadius: 12,
    marginBottom: 30,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2d3748',
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: '#4a5568',
    lineHeight: 20,
  },
});