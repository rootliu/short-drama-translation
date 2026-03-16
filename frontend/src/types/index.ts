export interface Project {
  id: number
  name: string
  description: string
  total_episodes: number
  batch_size: number
  target_language: string
  status: string
  created_at: string
  batch_count?: number
  completed_batches?: number
  total_eps?: number
  completed_eps?: number
  batches?: BatchInfo[]
  characters?: Character[]
}

export interface BatchInfo {
  id: number
  batch_number: number
  start_episode: number
  end_episode: number
  status: string
  progress: number
  started_at: string | null
  completed_at: string | null
  episode_count: number
  completed_count: number
}

export interface EpisodeListItem {
  id: number
  episode_number: number
  title: string
  duration_seconds: number
  status: string
  current_stage: string
  s1_status: string
  s2_status: string
  s3_status: string
  s5_status: string
  s6_status: string
  s7_status: string
  qa_status: string
  qa_passed: boolean | null
}

export interface DialogueLine {
  speaker: string
  text: string
  emotion: string
  score: number
  index?: number
  audio_emotion?: string
  text_emotion?: string
  confidence?: number
}

export interface EpisodeDetail {
  id: number
  episode_number: number
  title: string
  duration_seconds: number
  status: string
  current_stage: string
  stages: Record<string, string>
  subtitle_data: {
    total_lines: number
    duration: number
    asr_match_rate: number
    speakers_detected: number
    dialogues: DialogueLine[]
  } | null
  characters: Character[] | null
  emotions: {
    dialogues: DialogueLine[]
    peak_emotion: DialogueLine
    average_intensity: number
  } | null
  script: string | null
  summary: string | null
  emotion_analysis: {
    arc_type: string
    peak_time: string
    reversals: Array<{
      index: number
      from_emotion: string
      from_score: number
      to_emotion: string
      to_score: number
      delta: number
    }>
    average_intensity: number
  } | null
  hooks: {
    type: string
    content: string
    attraction_score: number
    translation_risk: string
    risk_reason: string
    continuity_score: number
  } | null
  qa_result: {
    overall_score: number
    asr_quality: number
    character_consistency: number
    emotion_calibration: number
    issues: string[]
    passed: boolean
  } | null
}

export interface Character {
  id?: number
  name: string
  aliases: string[]
  description: string
  role?: string
}

export interface PipelineLog {
  id: number
  stage: string
  level: string
  message: string
  timestamp: string
  episode_id: number | null
  batch_id: number | null
}

export interface ProjectStats {
  total_episodes: number
  completed_episodes: number
  processing_episodes: number
  avg_emotion_intensity: number
  total_reversals: number
  arc_type_distribution: Record<string, number>
  hook_type_distribution: Record<string, number>
  qa_pass_rate: number
}

export interface StageConfig {
  stages: Record<string, { name: string; depends_on: string[] }>
  phases: Record<string, { name: string; stages: string[]; active: boolean }>
}
