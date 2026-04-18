use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::process::Command;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Project {
    pub name: String,
    pub path: PathBuf,
    pub seed: String,
    pub phase: String,
    pub current_chapter: u32,
    pub total_chapters: u32,
    pub words_written: u32,
    pub average_score: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Chapter {
    pub number: u32,
    pub title: String,
    pub content: String,
    pub word_count: u32,
    pub score: Option<f32>,
    pub has_revision: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FoundationDoc {
    pub name: String,
    pub content: String,
    pub score: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PipelineState {
    pub phase: String,
    pub foundation_scores: FoundationScores,
    pub chapters: Vec<ChapterSummary>,
    pub revision_cycles: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FoundationScores {
    pub world: f32,
    pub characters: f32,
    pub outline: f32,
    pub canon: f32,
    pub voice: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChapterSummary {
    pub number: u32,
    pub title: String,
    pub word_count: u32,
    pub score: Option<f32>,
}

// Get current project directory (cwd)
#[tauri::command]
fn get_project_path() -> Result<String, String> {
    Ok(std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())?)
}

// Read seed.txt
#[tauri::command]
fn read_seed() -> Result<String, String> {
    let seed = fs::read_to_string("seed.txt").map_err(|e| e.to_string())?;
    Ok(seed.trim().to_string())
}

// Write seed.txt
#[tauri::command]
fn write_seed(seed: String) -> Result<(), String> {
    fs::write("seed.txt", seed).map_err(|e| e.to_string())
}

// Read state.json
#[tauri::command]
fn read_state() -> Result<PipelineState, String> {
    let state_path = PathBuf::from(".novelforge/state.json");
    if !state_path.exists() {
        return Ok(PipelineState {
            phase: "none".to_string(),
            foundation_scores: FoundationScores {
                world: 0.0,
                characters: 0.0,
                outline: 0.0,
                canon: 0.0,
                voice: 0.0,
            },
            chapters: vec![],
            revision_cycles: 0,
        });
    }
    let content = fs::read_to_string(state_path).map_err(|e| e.to_string())?;
    let state: serde_json::Value = serde_json::from_str(&content).map_err(|e| e.to_string())?;

    // Parse foundation scores
    let foundation = state.get("foundation").cloned().unwrap_or_default();
    let fscores = FoundationScores {
        world: foundation.get("world").and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        characters: foundation.get("characters").and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        outline: foundation.get("outline").and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        canon: foundation.get("canon").and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        voice: foundation.get("voice").and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
    };

    // Parse chapter scores
    let chapter_scores = state.get("chapter_scores").cloned().unwrap_or_default();
    let mut chapters: Vec<ChapterSummary> = Vec::new();
    if let Some(obj) = chapter_scores.as_object() {
        for (key, value) in obj {
            if key.starts_with("ch_") {
                let num_str = key.strip_prefix("ch_").unwrap_or("0");
                if let (Ok(num), Some(score)) = (num_str.parse::<u32>(), value.as_f64()) {
                    chapters.push(ChapterSummary {
                        number: num,
                        title: format!("Chapter {}", num),
                        word_count: 0,
                        score: Some(score as f32),
                    });
                }
            }
        }
    }
    chapters.sort_by_key(|c| c.number);

    Ok(PipelineState {
        phase: state.get("phase").and_then(|v| v.as_str()).unwrap_or("none").to_string(),
        foundation_scores: fscores,
        chapters,
        revision_cycles: state.get("revision_cycles").and_then(|v| v.as_u64()).map(|v| v as u32).unwrap_or(0),
    })
}

// Read a chapter file
#[tauri::command]
fn read_chapter(chapter_num: u32) -> Result<Chapter, String> {
    let chapter_path = PathBuf::from(format!("chapters/ch_{:02}.md", chapter_num));
    let content = fs::read_to_string(&chapter_path).map_err(|e| e.to_string())?;

    let revision_path = PathBuf::from(format!("chapters/ch_{:02}_revised.md", chapter_num));
    let has_revision = revision_path.exists();

    let word_count = content.split_whitespace().count() as u32;

    // Try to extract title from first heading
    let title = extract_title(&content).unwrap_or_else(|| format!("Chapter {}", chapter_num));

    Ok(Chapter {
        number: chapter_num,
        title,
        content,
        word_count,
        score: None,
        has_revision,
    })
}

// Read a foundation document
#[tauri::command]
fn read_foundation_doc(name: String) -> Result<FoundationDoc, String> {
    let path = match name.as_str() {
        "world" | "characters" | "outline" | "canon" | "voice" => PathBuf::from(format!("{}.md", name)),
        _ => return Err("Unknown document".to_string()),
    };

    let content = fs::read_to_string(&path).map_err(|e| e.to_string())?;

    Ok(FoundationDoc {
        name: name.clone(),
        content,
        score: 0.0, // TODO: Get from state
    })
}

// Extract title from markdown content
fn extract_title(content: &str) -> Option<String> {
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("# ") {
            return Some(trimmed.strip_prefix("# ").unwrap().to_string());
        }
    }
    None
}

// Run pipeline command
#[tauri::command]
async fn run_pipeline_phase(phase: String, cwd: String) -> Result<String, String> {
    let output = Command::new("python")
        .args(["run_pipeline.py", "--phase", &phase])
        .current_dir(&cwd)
        .output()
        .map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if !output.status.success() {
        return Err(format!("Pipeline failed: {}\n{}", stdout, stderr));
    }

    Ok(stdout)
}

// Run full pipeline
#[tauri::command]
async fn run_full_pipeline(cwd: String) -> Result<String, String> {
    let output = Command::new("python")
        .args(["run_pipeline.py", "--full"])
        .current_dir(&cwd)
        .output()
        .map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        return Err(stdout);
    }

    Ok(stdout)
}

// Save chapter content
#[tauri::command]
fn save_chapter(chapter_num: u32, content: String) -> Result<(), String> {
    let path = PathBuf::from(format!("chapters/ch_{:02}.md", chapter_num));
    fs::write(&path, content).map_err(|e| e.to_string())
}

// List all chapters
#[tauri::command]
fn list_chapters() -> Result<Vec<ChapterSummary>, String> {
    let chapters_dir = PathBuf::from("chapters");
    if !chapters_dir.exists() {
        return Ok(vec![]);
    }

    let mut chapters: Vec<ChapterSummary> = Vec::new();

    for entry in fs::read_dir(chapters_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let filename = entry.file_name().to_string_lossy().to_string();

        if filename.starts_with("ch_") && filename.ends_with(".md") {
            let num_str = filename.strip_prefix("ch_").unwrap().strip_suffix(".md").unwrap();
            if let Ok(num) = num_str.parse::<u32>() {
                let content = fs::read_to_string(entry.path()).unwrap_or_default();
                let word_count = content.split_whitespace().count() as u32;
                let title = extract_title(&content).unwrap_or_else(|| format!("Chapter {}", num));

                chapters.push(ChapterSummary {
                    number: num,
                    title,
                    word_count,
                    score: None,
                });
            }
        }
    }

    chapters.sort_by_key(|c| c.number);
    Ok(chapters)
}

// Check if project exists
#[tauri::command]
fn project_exists() -> bool {
    PathBuf::from("seed.txt").exists() || PathBuf::from(".novelforge/state.json").exists()
}

// Get manuscript text
#[tauri::command]
fn get_manuscript() -> Result<String, String> {
    let path = PathBuf::from("manuscript.md");
    if path.exists() {
        fs::read_to_string(&path).map_err(|e| e.to_string())
    } else {
        Ok(String::new())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_project_path,
            read_seed,
            write_seed,
            read_state,
            read_chapter,
            read_foundation_doc,
            run_pipeline_phase,
            run_full_pipeline,
            save_chapter,
            list_chapters,
            project_exists,
            get_manuscript,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
