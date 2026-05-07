import 'dart:convert';
import 'package:http/http.dart' as http;

// ─────────────────────────────────────────────────────────────
// CogniScan — Word Recall Service (Flutter side)
// Replace BASE_URL with your Render URL after deployment
// ─────────────────────────────────────────────────────────────

const String BASE_URL = 'https://cogni-word-recall.onrender.com';

class WordRecallService {
  // ── Step 1: Start test, get words ──────────────────────────
  static Future<WordRecallSession> startTest({
    required String patientId,
    required int age,
    required int educationYears,
    String language = 'en',
  }) async {
    final response = await http.post(
      Uri.parse('$BASE_URL/api/test/word-recall/start'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'patient_id': patientId,
        'age': age,
        'education_years': educationYears,
        'language': language,
      }),
    );

    if (response.statusCode == 200) {
      return WordRecallSession.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to start word recall test: ${response.body}');
    }
  }

  // ── Step 2: Submit recall results, get score ───────────────
  static Future<WordRecallResult> submitRecall({
    required String sessionId,
    required String patientId,
    required int age,
    required int educationYears,
    required List<String> wordsShown,
    required List<String> immediateRecall,
    required int immediateRecallTimeMs,
    List<int>? perWordTimeMs,
    List<String>? delayedRecall,
    int? delayedRecallTimeMs,
    int? yesNoScore,
    String language = 'en',
  }) async {
    final response = await http.post(
      Uri.parse('$BASE_URL/api/test/word-recall/submit'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'session_id': sessionId,
        'patient_id': patientId,
        'age': age,
        'education_years': educationYears,
        'language': language,
        'words_shown': wordsShown,
        'immediate_recall': immediateRecall,
        'immediate_recall_time_ms': immediateRecallTimeMs,
        'per_word_time_ms': perWordTimeMs,
        'distractor_completed': true,
        'delayed_recall': delayedRecall,
        'delayed_recall_time_ms': delayedRecallTimeMs,
        if (yesNoScore != null) 'yes_no_score': yesNoScore,
      }),
    );

    if (response.statusCode == 200) {
      return WordRecallResult.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to submit recall: ${response.body}');
    }
  }
}

// ─── Data Models ──────────────────────────────────────────────

class WordRecallSession {
  final String sessionId;
  final List<String> words;
  final double displayDurationSeconds;
  final int yesNoTimeoutSeconds;
  final Map<String, dynamic> distractorTask;
  final int distractorDurationSeconds;

  WordRecallSession({
    required this.sessionId,
    required this.words,
    required this.displayDurationSeconds,
    required this.yesNoTimeoutSeconds,
    required this.distractorTask,
    required this.distractorDurationSeconds,
  });

  factory WordRecallSession.fromJson(Map<String, dynamic> json) {
    return WordRecallSession(
      sessionId: json['session_id'],
      words: List<String>.from(json['words']),
      displayDurationSeconds: (json['display_duration_seconds'] as num).toDouble(),
      yesNoTimeoutSeconds: json['yes_no_timeout_seconds'],
      distractorTask: json['distractor_task'],
      distractorDurationSeconds: json['distractor_duration_seconds'],
    );
  }
}

class WordRecallResult {
  final String sessionId;
  final String patientId;
  final double immediateRecallScore;
  final double? delayedRecallScore;
  final int intrusionErrors;
  final double memoryScore;        // 0-10 — send this to aggregator
  final String encodingEfficiency;
  final double? retentionRatio;
  final List<String> clinicalFlags;
  final String interpretation;
  final Map<String, dynamic> rawData;

  WordRecallResult({
    required this.sessionId,
    required this.patientId,
    required this.immediateRecallScore,
    this.delayedRecallScore,
    required this.intrusionErrors,
    required this.memoryScore,
    required this.encodingEfficiency,
    this.retentionRatio,
    required this.clinicalFlags,
    required this.interpretation,
    required this.rawData,
  });

  factory WordRecallResult.fromJson(Map<String, dynamic> json) {
    return WordRecallResult(
      sessionId: json['session_id'],
      patientId: json['patient_id'],
      immediateRecallScore: (json['immediate_recall_score'] as num).toDouble(),
      delayedRecallScore: json['delayed_recall_score'] != null
          ? (json['delayed_recall_score'] as num).toDouble()
          : null,
      intrusionErrors: json['intrusion_errors'],
      memoryScore: (json['memory_score'] as num).toDouble(),
      encodingEfficiency: json['encoding_efficiency'],
      retentionRatio: json['retention_ratio'] != null
          ? (json['retention_ratio'] as num).toDouble()
          : null,
      clinicalFlags: List<String>.from(json['clinical_flags']),
      interpretation: json['interpretation'],
      rawData: json['raw_data'],
    );
  }
}
