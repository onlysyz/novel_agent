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
    // First: check if current directory itself is a project
    if std::path::Path::new(".novelforge/state.json").exists() {
        return std::env::current_dir()
            .map(|p| p.to_string_lossy().to_string())
            .map_err(|e| e.to_string());
    }

    // Search: check common subdirectory patterns under home
    if let Ok(home) = std::env::var("HOME") {
        let home = std::path::PathBuf::from(&home);
        let candidates = [
            home.join("workspace"),
            home.join("Projects"),
            home.join("Documents"),
            home.join("code"),
        ];

        for base in &candidates {
            if base.is_dir() {
                if let Ok(entries) = fs::read_dir(base) {
                    for entry in entries.flatten() {
                        let path = entry.path();
                        if path.is_dir() {
                            let state_file = path.join(".novelforge/state.json");
                            if state_file.exists() {
                                return Ok(path.to_string_lossy().to_string());
                            }
                        }
                    }
                }
            }
        }
    }

    // Fall back to current directory
    std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())
}

// Read seed.txt
#[tauri::command]
fn read_seed(cwd: String) -> Result<String, String> {
    let path = PathBuf::from(&cwd).join("seed.txt");
    let seed = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    Ok(seed.trim().to_string())
}

// Write seed.txt
#[tauri::command]
fn write_seed(cwd: String, seed: String) -> Result<(), String> {
    let path = PathBuf::from(&cwd).join("seed.txt");
    fs::write(&path, seed).map_err(|e| e.to_string())
}

// Read state.json
#[tauri::command]
fn read_state(cwd: String) -> Result<PipelineState, String> {
    let base = PathBuf::from(&cwd);
    let state_path = base.join(".novelforge/state.json");
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

    // Parse chapter scores (nested under drafting.chapter_scores)
    let drafting = state.get("drafting").cloned().unwrap_or_default();
    let chapter_scores = drafting.get("chapter_scores").cloned().unwrap_or_default();
    let chapters_dir = base.join("chapters");
    let mut chapters: Vec<ChapterSummary> = Vec::new();
    if let Some(obj) = chapter_scores.as_object() {
        for (key, value) in obj {
            if key.starts_with("ch_") {
                let num_str = key.strip_prefix("ch_").unwrap_or("0");
                if let (Ok(num), Some(score)) = (num_str.parse::<u32>(), value.as_f64()) {
                    let word_count = if chapters_dir.exists() {
                        let chapter_path = chapters_dir.join(format!("ch_{:02}.md", num));
                        fs::read_to_string(&chapter_path)
                            .map(|c| c.split_whitespace().count() as u32)
                            .unwrap_or(0)
                    } else {
                        0
                    };
                    chapters.push(ChapterSummary {
                        number: num,
                        title: format!("Chapter {}", num),
                        word_count,
                        score: Some(score as f32),
                    });
                }
            }
        }
    }
    chapters.sort_by_key(|c| c.number);

    // Parse revision cycles (nested under review.revision_cycles)
    let review = state.get("review").cloned().unwrap_or_default();
    let revision_cycles = review.get("revision_cycles").and_then(|v| v.as_u64()).map(|v| v as u32).unwrap_or(0);

    Ok(PipelineState {
        phase: state.get("phase").and_then(|v| v.as_str()).unwrap_or("none").to_string(),
        foundation_scores: fscores,
        chapters,
        revision_cycles,
    })
}

// Read a chapter file
#[tauri::command]
fn read_chapter(cwd: String, chapter_num: u32) -> Result<Chapter, String> {
    let base = PathBuf::from(&cwd);
    let chapter_path = base.join(format!("chapters/ch_{:02}.md", chapter_num));
    let content = fs::read_to_string(&chapter_path).map_err(|e| e.to_string())?;

    let revision_path = base.join(format!("chapters/ch_{:02}_revised.md", chapter_num));
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
fn read_foundation_doc(cwd: String, name: String) -> Result<FoundationDoc, String> {
    let path = match name.as_str() {
        "world" | "characters" | "outline" | "canon" | "voice" => PathBuf::from(&cwd).join(format!("{}.md", name)),
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
    let python = if Command::new("python3").arg("--version").output().is_ok() {
        "python3"
    } else {
        "python"
    };
    let output = Command::new(python)
        .env("PYTHONPATH", &cwd)
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
    let python = if Command::new("python3").arg("--version").output().is_ok() {
        "python3"
    } else {
        "python"
    };
    let output = Command::new(python)
        .env("PYTHONPATH", &cwd)
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
fn save_chapter(cwd: String, chapter_num: u32, content: String) -> Result<(), String> {
    let path = PathBuf::from(&cwd).join(format!("chapters/ch_{:02}.md", chapter_num));
    fs::write(&path, content).map_err(|e| e.to_string())
}

// List all chapters
#[tauri::command]
fn list_chapters(cwd: String) -> Result<Vec<ChapterSummary>, String> {
    let base = PathBuf::from(&cwd);
    let chapters_dir = base.join("chapters");
    if !chapters_dir.exists() {
        return Ok(vec![]);
    }

    // Read chapter scores from state.json
    let chapter_scores: std::collections::HashMap<String, f64> = {
        let state_path = base.join(".novelforge/state.json");
        if state_path.exists() {
            let content = fs::read_to_string(&state_path).unwrap_or_default();
            let json: serde_json::Value = serde_json::from_str(&content).unwrap_or_default();
            let drafting = json.get("drafting").unwrap_or(&serde_json::Value::Null);
            let scores = drafting.get("chapter_scores").unwrap_or(&serde_json::Value::Null);
            scores.as_object()
                .map(|obj| {
                    obj.iter()
                        .filter_map(|(k, v)| v.as_f64().map(|score| (k.clone(), score)))
                        .collect()
                })
                .unwrap_or_default()
        } else {
            std::collections::HashMap::new()
        }
    };

    let mut chapters: Vec<ChapterSummary> = Vec::new();

    for entry in fs::read_dir(&chapters_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let filename = entry.file_name().to_string_lossy().to_string();

        if filename.starts_with("ch_") && filename.ends_with(".md") {
            let num_str = filename.strip_prefix("ch_").unwrap().strip_suffix(".md").unwrap();
            if let Ok(num) = num_str.parse::<u32>() {
                let content = fs::read_to_string(entry.path()).unwrap_or_default();
                let word_count = content.split_whitespace().count() as u32;
                let title = extract_title(&content).unwrap_or_else(|| format!("Chapter {}", num));
                let score_key = format!("ch_{:02}", num);
                let score = chapter_scores.get(&score_key).map(|&s| s as f32);

                chapters.push(ChapterSummary {
                    number: num,
                    title,
                    word_count,
                    score,
                });
            }
        }
    }

    chapters.sort_by_key(|c| c.number);
    Ok(chapters)
}

// Check if project exists
#[tauri::command]
fn project_exists(cwd: String) -> bool {
    let base = PathBuf::from(&cwd);
    base.join("seed.txt").exists() || base.join(".novelforge/state.json").exists()
}

// Get manuscript text
#[tauri::command]
fn get_manuscript(cwd: String) -> Result<String, String> {
    let path = PathBuf::from(&cwd).join("manuscript.md");
    if path.exists() {
        fs::read_to_string(&path).map_err(|e| e.to_string())
    } else {
        Ok(String::new())
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ExportFile {
    pub name: String,
    pub format: String,
    pub size_bytes: u64,
    pub modified: String,
    pub path: String,
}

// List available export files
#[tauri::command]
fn list_exports(cwd: String) -> Result<Vec<ExportFile>, String> {
    let export_dir = PathBuf::from(&cwd).join("export");
    if !export_dir.exists() {
        return Ok(vec![]);
    }

    let mut files = Vec::new();
    for entry in fs::read_dir(&export_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        if path.is_file() {
            let name = path.file_name().unwrap().to_string_lossy().to_string();
            let ext = path.extension().unwrap_or_default().to_string_lossy().to_lowercase();
            let format = match ext.as_str() {
                "txt" => "text",
                "epub" => "epub",
                "pdf" => "pdf",
                "png" | "jpg" | "jpeg" => "image",
                _ => "other",
            };
            let metadata = fs::metadata(&path).map_err(|e| e.to_string())?;
            let modified = metadata.modified()
                .ok()
                .and_then(|t| format_datetime(t))
                .unwrap_or_else(|| "unknown".to_string());
            files.push(ExportFile {
                name,
                format: format.to_string(),
                size_bytes: metadata.len(),
                modified,
                path: path.to_string_lossy().to_string(),
            });
        }
    }
    files.sort_by_key(|f| f.name.clone());
    Ok(files)
}

// Format SystemTime as ISO 8601 date string without external crates
fn format_datetime(time: std::time::SystemTime) -> Option<String> {
    let duration = time.duration_since(std::time::UNIX_EPOCH).ok()?;
    let secs = duration.as_secs();

    // Count days from epoch
    let days = secs / 86400;
    let rem = secs % 86400;
    let hour = rem / 3600;
    let minutes = (rem % 3600) / 60;
    let _sec = rem % 60;

    // Find year by counting days from 1970
    let (year, yday) = iso_day_of_year(days as i64)?;

    // Approximate month/day from day-of-year
    let is_leap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    let days_in_month: [u64; 12] = if is_leap {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };

    let mut month: u64 = 1;
    let mut remaining = yday;
    for (i, &dim) in days_in_month.iter().enumerate() {
        if remaining < dim {
            month = i as u64 + 1;
            break;
        }
        remaining -= dim;
    }
    let day = remaining + 1;

    Some(format!("{:04}-{:02}-{:02} {:02}:{:02}", year, month, day, hour, minutes))
}

// Compute year and day-of-year from days since 1970-01-01
fn iso_day_of_year(days: i64) -> Option<(i64, u64)> {
    // Simple algorithm: 400-year cycles have 146097 days
    let mut d = days;
    let mut year = 1970;

    // Handle negative days (before 1970)
    if d < 0 {
        let cycles = (d + 1) / 146097 - 1;
        d -= cycles * 146097;
        year += cycles * 400;
    }

    // Count 400-year cycles
    let cycles400 = d / 146097;
    d -= cycles400 * 146097;
    year += cycles400 * 400;

    // Count 100-year cycles (max 3, since 4th would overlap next 400-cycle)
    let cycles100 = d / 36524;
    if cycles100 == 4 {
        // Last day of leap year cycle
        d -= 3 * 36524 + 366;
        year += 300;
    } else {
        d -= cycles100 * 36524;
        year += cycles100 * 100;
    }

    // Count 4-year cycles
    let cycles4 = d / 1461;
    d -= cycles4 * 1461;
    year += cycles4 * 4;

    // Count 1-year cycles
    let cycles1 = d / 365;
    if cycles1 == 4 {
        // Last year of 4-year cycle is leap
        year += 3;
        return Some((year, 365));
    }
    d -= cycles1 * 365;
    year += cycles1;

    let yday = d as u64;
    Some((year, yday))
}

// Read an export file and return as base64
#[tauri::command]
fn get_export_file(cwd: String, filename: String) -> Result<String, String> {
    let export_dir = PathBuf::from(&cwd).join("export");
    let path = export_dir.join(&filename);
    if !path.exists() {
        return Err(format!("File not found: {}", filename));
    }
    let bytes = fs::read(&path).map_err(|e| e.to_string())?;
    Ok(base64_encode(&bytes))
}

// Open a file with the system's default application
#[tauri::command]
fn open_export_file(cwd: String, filename: String) -> Result<(), String> {
    let export_dir = PathBuf::from(&cwd).join("export");
    let path = export_dir.join(&filename);
    if !path.exists() {
        return Err(format!("File not found: {}", filename));
    }
    let path_str = path.to_string_lossy();

    #[cfg(target_os = "macos")]
    {
        Command::new("open").arg(path_str.as_ref()).spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open").arg(path_str.as_ref()).spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", path_str.as_ref()])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
    {
        Err("Unsupported platform")?
    }
    Ok(())
}

fn base64_encode(data: &[u8]) -> String {
    const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::new();
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as usize;
        let b1 = chunk.get(1).copied().unwrap_or(0) as usize;
        let b2 = chunk.get(2).copied().unwrap_or(0) as usize;
        result.push(ALPHABET[b0 >> 2] as char);
        result.push(ALPHABET[((b0 & 0x03) << 4) | (b1 >> 4)] as char);
        if chunk.len() > 1 {
            result.push(ALPHABET[((b1 & 0x0f) << 2) | (b2 >> 6)] as char);
        } else {
            result.push('=');
        }
        if chunk.len() > 2 {
            result.push(ALPHABET[b2 & 0x3f] as char);
        } else {
            result.push('=');
        }
    }
    result
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
            list_exports,
            get_export_file,
            open_export_file,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
