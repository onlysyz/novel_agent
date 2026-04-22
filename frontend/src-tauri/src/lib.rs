use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::process::{Command, Child};
#[cfg(unix)]
use std::os::unix::process::ExitStatusExt;
use tauri::Emitter;

// ─────────────────────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────────────────────

fn count_chars(text: &str) -> usize {
    // Count CJK characters individually; count English words (space-separated)
    let mut count = 0;

    for seg in text.split_whitespace() {
        let seg_chars: Vec<char> = seg.chars().collect();
        let mut i = 0;
        while i < seg_chars.len() {
            let c = seg_chars[i];
            let code = c as u32;
            let is_cjk = (0x3000..=0x303F).contains(&code)
                || (0x4E00..=0x9FFF).contains(&code)
                || (0x3400..=0x4DBF).contains(&code)
                || (0x3040..=0x309F).contains(&code)
                || (0x30A0..=0x30FF).contains(&code)
                || (0xF900..=0xFAFF).contains(&code)
                || (0xFF00..=0xFFEF).contains(&code);
            if is_cjk {
                count += 1;
                i += 1;
            } else if c.is_ascii_alphabetic() {
                count += 1;
                while i < seg_chars.len() && seg_chars[i].is_ascii_alphabetic() {
                    i += 1;
                }
            } else {
                i += 1;
            }
        }
    }
    count
}

// ─────────────────────────────────────────────────────────────────────────────
// Data types
// ─────────────────────────────────────────────────────────────────────────────

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

#[derive(Debug, Serialize, Deserialize)]
pub struct AIConfig {
    pub api_key: String,
    pub base_url: String,
    pub model: String,
    pub opus_model: String,
    pub target_words: String,
    pub chapter_target: String,
    pub output_dir: String,
    pub novel_title: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ExportFile {
    pub name: String,
    pub format: String,
    pub size_bytes: u64,
    pub modified: String,
    pub path: String,
}

#[derive(Clone, serde::Serialize)]
struct PipelineProgress {
    phase: String,
    step: String,
    message: String,
}

// ─────────────────────────────────────────────────────────────────────────────
// Directory helpers
//
// There are exactly TWO directories in this system:
//
//   app_root   – where run_pipeline.py and the Python source lives.
//                Determined by walking up from the process CWD / binary path
//                until run_pipeline.py is found.  Never configurable by the user.
//
//   output_dir – where ALL generated novel files are written:
//                seed.txt, world.md, chapters/, .novelforge/state.json, etc.
//                Configured by the user in Settings; stored as the "output_dir"
//                field inside app_root/.novelforge/config.json (the bootstrap
//                pointer).  When not configured it falls back to app_root.
//
// Rule: every Tauri command that reads/writes novel files takes `output_dir`
//       as its first parameter (named exactly that so the JS caller must be
//       explicit).  Commands that spawn Python scripts call find_app_root()
//       internally — they never receive app_root from the frontend.
// ─────────────────────────────────────────────────────────────────────────────

/// Walk upward from the process CWD (then from the binary) until we find the
/// directory that contains `run_pipeline.py`.  This is always the source repo.
fn find_app_root() -> PathBuf {
    // 1. Walk up from process CWD
    if let Ok(cwd) = std::env::current_dir() {
        let mut dir: &std::path::Path = cwd.as_path();
        loop {
            if dir.join("run_pipeline.py").exists() {
                return dir.to_path_buf();
            }
            match dir.parent() {
                Some(p) => dir = p,
                None => break,
            }
        }
    }
    // 2. Walk up from the executable path
    if let Ok(exe) = std::env::current_exe() {
        let mut cur = exe.parent().map(|p| p.to_path_buf());
        for _ in 0..6 {
            if let Some(ref d) = cur {
                if d.join("run_pipeline.py").exists() {
                    return d.clone();
                }
                cur = d.parent().map(|p| p.to_path_buf());
            }
        }
    }
    // 3. Fallback (should never happen in practice)
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

/// Find the right Python interpreter, always relative to `app_root` where the
/// `.venv` lives.  Never uses $PATH (GUI apps have a stripped PATH on macOS).
fn find_python(app_root: &std::path::Path) -> String {
    let venv = app_root.join(".venv/bin/python3");
    if venv.exists() {
        return venv.to_string_lossy().to_string();
    }
    for p in &[
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
    ] {
        if std::path::Path::new(p).exists() {
            return p.to_string();
        }
    }
    "python3".to_string()
}

// ─────────────────────────────────────────────────────────────────────────────
// Discovery command – returns output_dir to the frontend
// ─────────────────────────────────────────────────────────────────────────────

/// Return the project output directory (where novel files live).
///
/// Resolution order:
///   1. Read "output_dir" from app_root/.novelforge/config.json.
///      If it's set and the path exists (or can be created) → return it.
///   2. Fall back to app_root itself (no separate output configured).
#[tauri::command]
fn get_project_path() -> Result<String, String> {
    let app_root = find_app_root();
    let config_path = app_root.join(".novelforge/config.json");

    if config_path.exists() {
        if let Ok(content) = fs::read_to_string(&config_path) {
            if let Ok(cfg) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(dir) = cfg.get("output_dir").and_then(|v| v.as_str()).filter(|s| !s.is_empty()) {
                    let p = PathBuf::from(dir);
                    // Create the directory if it does not yet exist
                    if !p.exists() {
                        fs::create_dir_all(&p).map_err(|e| e.to_string())?;
                    }
                    return Ok(dir.to_string());
                }
            }
        }
    }

    // No separate output_dir configured → use app_root
    Ok(app_root.to_string_lossy().to_string())
}

// ─────────────────────────────────────────────────────────────────────────────
// Novel-file commands  (all take `output_dir` – the project/novel directory)
// ─────────────────────────────────────────────────────────────────────────────

/// Read seed.txt from output_dir, stripping the [language: xx] header.
#[tauri::command]
fn read_seed(output_dir: String) -> Result<String, String> {
    let path = PathBuf::from(&output_dir).join("seed.txt");
    let content = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let seed = if content.starts_with("[language:") {
        content
            .lines()
            .skip_while(|l| l.starts_with("[language:"))
            .skip(1)
            .collect::<Vec<_>>()
            .join("\n")
    } else {
        content
    };
    Ok(seed.trim().to_string())
}

/// Read the language code from seed.txt header in output_dir.
#[tauri::command]
fn read_language(output_dir: String) -> Result<String, String> {
    let path = PathBuf::from(&output_dir).join("seed.txt");
    let content = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    for line in content.lines() {
        if line.starts_with("[language:") {
            let lang = line
                .strip_prefix("[language:")
                .unwrap_or("")
                .trim_end_matches(']')
                .trim();
            return Ok(lang.to_string());
        }
    }
    Ok("en".to_string())
}

/// Write seed.txt (with language header) into output_dir.
#[tauri::command]
fn write_seed(output_dir: String, seed: String, language: String) -> Result<(), String> {
    let path = PathBuf::from(&output_dir).join("seed.txt");
    let content = format!("[language: {}]\n{}", language, seed);
    fs::write(&path, content).map_err(|e| e.to_string())
}

/// Read AI/project config from output_dir/.novelforge/config.json.
#[tauri::command]
fn read_ai_config(output_dir: String) -> Result<AIConfig, String> {
    let config_path = PathBuf::from(&output_dir).join(".novelforge/config.json");
    if config_path.exists() {
        let content = fs::read_to_string(&config_path).map_err(|e| e.to_string())?;
        serde_json::from_str(&content).map_err(|e| e.to_string())
    } else {
        Ok(AIConfig {
            api_key: String::new(),
            base_url: String::new(),
            model: "claude-sonnet-4-20250514".to_string(),
            opus_model: "opus-4-5-20251114".to_string(),
            target_words: "80000".to_string(),
            chapter_target: "22".to_string(),
            output_dir: String::new(),
            novel_title: String::new(),
        })
    }
}

/// Write AI/project config to output_dir/.novelforge/config.json.
/// Also updates the "output_dir" pointer in app_root/.novelforge/config.json
/// so that get_project_path() finds it next time.
#[tauri::command]
fn write_ai_config(output_dir: String, config: AIConfig) -> Result<(), String> {
    // 1. Write full config to output_dir
    let dotnovel = PathBuf::from(&output_dir).join(".novelforge");
    fs::create_dir_all(&dotnovel).map_err(|e| e.to_string())?;
    let config_path = dotnovel.join("config.json");
    let content = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    fs::write(&config_path, &content).map_err(|e| e.to_string())?;

    // 2. Keep the bootstrap pointer in app_root up-to-date so that
    //    get_project_path() reliably returns output_dir on next launch.
    let new_output_dir = if config.output_dir.is_empty() {
        output_dir.clone()
    } else {
        config.output_dir.clone()
    };
    let app_root = find_app_root();
    let app_config_path = app_root.join(".novelforge/config.json");
    // Only write the pointer if app_root differs from output_dir
    if app_config_path != config_path {
        let mut pointer: serde_json::Value = if app_config_path.exists() {
            fs::read_to_string(&app_config_path)
                .ok()
                .and_then(|c| serde_json::from_str(&c).ok())
                .unwrap_or_else(|| serde_json::json!({}))
        } else {
            serde_json::json!({})
        };
        pointer["output_dir"] = serde_json::Value::String(new_output_dir);
        let _ = fs::create_dir_all(app_root.join(".novelforge"));
        let _ = fs::write(
            &app_config_path,
            serde_json::to_string_pretty(&pointer).unwrap_or_default(),
        );
    }

    Ok(())
}

/// Delete all generated novel files from output_dir (for "start fresh").
#[tauri::command]
fn reset_project_state(output_dir: String) -> Result<(), String> {
    let base = PathBuf::from(&output_dir);
    let state_path = base.join(".novelforge/state.json");
    if state_path.exists() {
        fs::remove_file(&state_path).map_err(|e| e.to_string())?;
    }
    for f in &["voice.md", "world.md", "characters.md", "outline.md", "canon.md", "manuscript.md"] {
        let path = base.join(f);
        if path.exists() {
            fs::remove_file(&path).map_err(|e| e.to_string())?;
        }
    }
    let chapters_dir = base.join("chapters");
    if chapters_dir.exists() {
        fs::remove_dir_all(&chapters_dir).map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Read pipeline state from output_dir/.novelforge/state.json.
#[tauri::command]
fn read_state(output_dir: String) -> Result<PipelineState, String> {
    let base = PathBuf::from(&output_dir);
    let state_path = base.join(".novelforge/state.json");
    if !state_path.exists() {
        return Ok(PipelineState {
            phase: "none".to_string(),
            foundation_scores: FoundationScores { world: 0.0, characters: 0.0, outline: 0.0, canon: 0.0, voice: 0.0 },
            chapters: vec![],
            revision_cycles: 0,
        });
    }
    let content = fs::read_to_string(&state_path).map_err(|e| e.to_string())?;
    let state: serde_json::Value = serde_json::from_str(&content).map_err(|e| e.to_string())?;

    let foundation = state.get("foundation").cloned().unwrap_or_default();
    let fscores = FoundationScores {
        world:      foundation.get("world")     .and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        characters: foundation.get("characters").and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        outline:    foundation.get("outline")   .and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        canon:      foundation.get("canon")     .and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
        voice:      foundation.get("voice")     .and_then(|v| v.get("score")).and_then(|v| v.as_f64()).map(|v| v as f32).unwrap_or(0.0),
    };

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
                        let cp = chapters_dir.join(format!("ch_{:02}.md", num));
                        fs::read_to_string(&cp).map(|c| count_chars(&c) as u32).unwrap_or(0)
                    } else { 0 };
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

    let review = state.get("review").cloned().unwrap_or_default();
    let revision_cycles = review.get("revision_cycles").and_then(|v| v.as_u64()).map(|v| v as u32).unwrap_or(0);

    Ok(PipelineState {
        phase: state.get("phase").and_then(|v| v.as_str()).unwrap_or("none").to_string(),
        foundation_scores: fscores,
        chapters,
        revision_cycles,
    })
}

/// Read a chapter file from output_dir/chapters/.
#[tauri::command]
fn read_chapter(output_dir: String, chapter_num: u32) -> Result<Chapter, String> {
    let base = PathBuf::from(&output_dir);
    let chapter_path = base.join(format!("chapters/ch_{:02}.md", chapter_num));
    let content = fs::read_to_string(&chapter_path).map_err(|e| e.to_string())?;
    let revision_path = base.join(format!("chapters/ch_{:02}_revised.md", chapter_num));
    let has_revision = revision_path.exists();
    let word_count = count_chars(&content) as u32;
    let title = extract_title(&content).unwrap_or_else(|| format!("Chapter {}", chapter_num));
    Ok(Chapter { number: chapter_num, title, content, word_count, score: None, has_revision })
}

/// Read a foundation document (world/characters/outline/canon/voice) from output_dir.
#[tauri::command]
fn read_foundation_doc(output_dir: String, name: String) -> Result<FoundationDoc, String> {
    let path = match name.as_str() {
        "world" | "characters" | "outline" | "canon" | "voice" =>
            PathBuf::from(&output_dir).join(format!("{}.md", name)),
        _ => return Err("Unknown document".to_string()),
    };
    let content = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    Ok(FoundationDoc { name, content, score: 0.0 })
}

/// Save a chapter file to output_dir/chapters/.
#[tauri::command]
fn save_chapter(output_dir: String, chapter_num: u32, content: String) -> Result<(), String> {
    let path = PathBuf::from(&output_dir).join(format!("chapters/ch_{:02}.md", chapter_num));
    fs::write(&path, content).map_err(|e| e.to_string())
}

/// List all chapters in output_dir/chapters/.
#[tauri::command]
fn list_chapters(output_dir: String) -> Result<Vec<ChapterSummary>, String> {
    let base = PathBuf::from(&output_dir);
    let chapters_dir = base.join("chapters");
    if !chapters_dir.exists() {
        return Ok(vec![]);
    }

    let chapter_scores: std::collections::HashMap<String, f64> = {
        let state_path = base.join(".novelforge/state.json");
        if state_path.exists() {
            let content = fs::read_to_string(&state_path).unwrap_or_default();
            let json: serde_json::Value = serde_json::from_str(&content).unwrap_or_default();
            json.get("drafting")
                .and_then(|d| d.get("chapter_scores"))
                .and_then(|s| s.as_object())
                .map(|obj| obj.iter().filter_map(|(k, v)| v.as_f64().map(|s| (k.clone(), s))).collect())
                .unwrap_or_default()
        } else {
            std::collections::HashMap::new()
        }
    };

    let mut chapters: Vec<ChapterSummary> = Vec::new();
    for entry in fs::read_dir(&chapters_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let filename = entry.file_name().to_string_lossy().to_string();
        if filename.starts_with("ch_") && filename.ends_with(".md") && !filename.contains("revised") {
            let num_str = filename.strip_prefix("ch_").unwrap().strip_suffix(".md").unwrap();
            if let Ok(num) = num_str.parse::<u32>() {
                let content = fs::read_to_string(entry.path()).unwrap_or_default();
                let word_count = count_chars(&content) as u32;
                let title = extract_title(&content).unwrap_or_else(|| format!("Chapter {}", num));
                let score_key = format!("ch_{:02}", num);
                let score = chapter_scores.get(&score_key).map(|&s| s as f32);
                chapters.push(ChapterSummary { number: num, title, word_count, score });
            }
        }
    }
    chapters.sort_by_key(|c| c.number);
    Ok(chapters)
}

/// Check whether a project exists in output_dir.
#[tauri::command]
fn project_exists(output_dir: String) -> bool {
    let base = PathBuf::from(&output_dir);
    base.join("seed.txt").exists() || base.join(".novelforge/state.json").exists()
}

/// Read manuscript.md from output_dir.
#[tauri::command]
fn get_manuscript(output_dir: String) -> Result<String, String> {
    let path = PathBuf::from(&output_dir).join("manuscript.md");
    if path.exists() { fs::read_to_string(&path).map_err(|e| e.to_string()) } else { Ok(String::new()) }
}

/// List export files under output_dir/export/.
#[tauri::command]
fn list_exports(output_dir: String) -> Result<Vec<ExportFile>, String> {
    let export_dir = PathBuf::from(&output_dir).join("export");
    if !export_dir.exists() { return Ok(vec![]); }
    let mut files = Vec::new();
    for entry in fs::read_dir(&export_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        if path.is_file() {
            let name = path.file_name().unwrap().to_string_lossy().to_string();
            let ext = path.extension().unwrap_or_default().to_string_lossy().to_lowercase();
            let format = match ext.as_str() {
                "txt" => "text", "epub" => "epub", "pdf" => "pdf",
                "png" | "jpg" | "jpeg" => "image", _ => "other",
            };
            let metadata = fs::metadata(&path).map_err(|e| e.to_string())?;
            let modified = metadata.modified().ok().and_then(format_datetime).unwrap_or_else(|| "unknown".to_string());
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

/// Return a base64-encoded export file from output_dir/export/.
#[tauri::command]
fn get_export_file(output_dir: String, filename: String) -> Result<String, String> {
    let path = PathBuf::from(&output_dir).join("export").join(&filename);
    if !path.exists() { return Err(format!("File not found: {}", filename)); }
    Ok(base64_encode(&fs::read(&path).map_err(|e| e.to_string())?))
}

/// Open an export file with the OS default application.
#[tauri::command]
fn open_export_file(output_dir: String, filename: String) -> Result<(), String> {
    let path = PathBuf::from(&output_dir).join("export").join(&filename);
    if !path.exists() { return Err(format!("File not found: {}", filename)); }
    let path_str = path.to_string_lossy();
    #[cfg(target_os = "macos")]
    { Command::new("open").arg(path_str.as_ref()).spawn().map_err(|e| e.to_string())?; }
    #[cfg(target_os = "linux")]
    { Command::new("xdg-open").arg(path_str.as_ref()).spawn().map_err(|e| e.to_string())?; }
    #[cfg(target_os = "windows")]
    { Command::new("cmd").args(["/C", "start", "", path_str.as_ref()]).spawn().map_err(|e| e.to_string())?; }
    Ok(())
}

// ─────────────────────────────────────────────────────────────────────────────
// Python-executing commands
// These commands always find app_root internally (never receive it from the
// frontend) and pass output_dir to Python via --output-dir.
// ─────────────────────────────────────────────────────────────────────────────

/// Generate a novel title using Python (runs src/foundation/gen_title.py in app_root).
/// Saves the title to output_dir/.novelforge/config.json.
#[tauri::command]
async fn generate_title(output_dir: String) -> Result<String, String> {
    let app_root = find_app_root();
    let python = find_python(&app_root);

    let output = Command::new(&python)
        .env("PYTHONPATH", app_root.to_str().unwrap_or(""))
        .args(["-c", "
import sys
sys.path.insert(0, '.')
from src.foundation.gen_title import generate_title
result = generate_title()
print(result['title'])
"])
        .current_dir(&app_root)
        .output()
        .map_err(|e| e.to_string())?;

    if !output.status.success() {
        return Err(format!("Failed to generate title: {}", String::from_utf8_lossy(&output.stderr)));
    }
    let title = String::from_utf8_lossy(&output.stdout).trim().to_string();

    // Save title into output_dir config
    let config_path = PathBuf::from(&output_dir).join(".novelforge/config.json");
    let mut config: AIConfig = if config_path.exists() {
        let content = fs::read_to_string(&config_path).map_err(|e| e.to_string())?;
        serde_json::from_str(&content).unwrap_or_else(|_| default_ai_config())
    } else {
        default_ai_config()
    };
    let dotnovel = PathBuf::from(&output_dir).join(".novelforge");
    fs::create_dir_all(&dotnovel).map_err(|e| e.to_string())?;
    config.novel_title = title.clone();
    fs::write(&config_path, serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;

    Ok(title)
}

fn default_ai_config() -> AIConfig {
    AIConfig {
        api_key: String::new(),
        base_url: String::new(),
        model: "claude-sonnet-4-20250514".to_string(),
        opus_model: "opus-4-5-20251114".to_string(),
        target_words: "80000".to_string(),
        chapter_target: "22".to_string(),
        output_dir: String::new(),
        novel_title: String::new(),
    }
}

// Mutex to prevent multiple pipelines from running simultaneously
use std::sync::Mutex;
static PIPELINE_RUNNING: Mutex<bool> = Mutex::new(false);

// ── Pipeline PID file management for crash recovery ────────────────────────────

fn get_pid_file(output_dir: &PathBuf) -> PathBuf {
    output_dir.join(".novelforge").join("pipeline.pid")
}

fn write_pid_file(output_dir: &PathBuf) -> std::io::Result<()> {
    let pid_file = get_pid_file(output_dir);
    let pid = std::process::id().to_string();
    fs::write(&pid_file, pid)?;
    Ok(())
}

fn remove_pid_file(output_dir: &PathBuf) {
    let pid_file = get_pid_file(output_dir);
    let _ = fs::remove_file(&pid_file);
}

fn is_pid_running(pid: u32) -> bool {
    // On macOS, check if process exists using `ps`
    match Command::new("ps").args(["-p", &pid.to_string()]).output() {
        Ok(output) => output.status.success(),
        Err(_) => false,
    }
}

/// Check if a pipeline is currently running (from a previous session)
fn check_previous_pipeline(output_dir: &PathBuf) -> bool {
    let pid_file = get_pid_file(output_dir);
    if pid_file.exists() {
        if let Ok(pid_str) = fs::read_to_string(&pid_file) {
            if let Ok(pid) = pid_str.trim().parse::<u32>() {
                if is_pid_running(pid) {
                    return true;
                }
            }
        }
        // PID file exists but process is not running - clean up
        let _ = fs::remove_file(&pid_file);
    }
    false
}

/// Check if a pipeline is currently running (for crash recovery)
#[tauri::command]
fn check_pipeline_status(output_dir: String) -> bool {
    let output_path = PathBuf::from(&output_dir);
    check_previous_pipeline(&output_path)
}

/// Run a specific pipeline phase.
/// - app_root   (internal): where run_pipeline.py and .venv live
/// - output_dir (from frontend): where generated novel files are written
#[tauri::command]
async fn run_pipeline_phase(
    phase: String,
    output_dir: String,
    app_handle: tauri::AppHandle,
) -> Result<(), String> {
    {
        let mut locked = PIPELINE_RUNNING.lock().unwrap();
        if *locked { return Err("Pipeline already running".to_string()); }
        *locked = true;
    }

    app_handle.emit("pipeline-started", &phase).map_err(|e| e.to_string())?;

    // Write PID file for crash recovery
    let output_path = PathBuf::from(&output_dir);
    if let Err(e) = write_pid_file(&output_path) {
        eprintln!("[Rust] Warning: failed to write PID file: {}", e);
    }

    std::thread::spawn(move || {
        let app_root = find_app_root();
        let python = find_python(&app_root);
        let script = app_root.join("run_pipeline.py");
        let progress_file = output_path.join(".novelforge").join("progress.jsonl");

        let args = vec![
            script.to_string_lossy().to_string(),
            "--phase".to_string(), phase.clone(),
            "--output-dir".to_string(), output_dir.clone(),
        ];

        let _ = app_handle.emit("pipeline-progress", PipelineProgress {
            phase: phase.clone(),
            step: "running".to_string(),
            message: format!("Running {} phase...", phase),
        });

        // Spawn child process without capturing stdout/stderr
        let child = match Command::new(&python)
            .env("PYTHONPATH", app_root.to_str().unwrap_or(""))
            .args(&args)
            .current_dir(&app_root)
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                *PIPELINE_RUNNING.lock().unwrap() = false;
                remove_pid_file(&output_path);
                let _ = app_handle.emit("pipeline-error",
                    format!("Failed to start Python ({}): {}", python, e));
                return;
            }
        };

        // Use Arc<Mutex<Option<Child>>> so the poll thread can check exit status
        use std::sync::{Arc, Mutex};
        let child: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(Some(child)));
        let child_poll = child.clone();
        let child_wait = child.clone();

        // File-polling thread: read progress.jsonl and emit events
        let app_handle_clone = app_handle.clone();
        let progress_file_clone = progress_file.clone();
        let phase_clone = phase.clone();
        let poll_thread = std::thread::spawn(move || {
            let mut last_pos = 0u64;
            for _ in 0..50 {
                if progress_file_clone.exists() { break; }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }

            loop {
                // Check if process exited
                let child_guard = child_poll.lock().unwrap();
                if child_guard.is_none() {
                    break;
                }
                drop(child_guard);

                if progress_file_clone.exists() {
                    if let Ok(metadata) = progress_file_clone.metadata() {
                        let current_size = metadata.len();
                        if current_size > last_pos {
                            if let Ok(mut file) = fs::File::open(&progress_file_clone) {
                                use std::io::{Seek, BufRead, BufReader};
                                if file.seek(std::io::SeekFrom::Start(last_pos)).is_ok() {
                                    let reader = BufReader::new(file);
                                    for line_result in reader.lines() {
                                        if let Ok(line) = line_result {
                                            if !line.is_empty() {
                                                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&line) {
                                                    let msg = json.get("message").and_then(|v| v.as_str()).unwrap_or("");
                                                    let step = json.get("step").and_then(|v| v.as_str()).unwrap_or("running");
                                                    let _ = app_handle_clone.emit("pipeline-progress", PipelineProgress {
                                                        phase: phase_clone.clone(),
                                                        step: step.to_string(),
                                                        message: msg.to_string(),
                                                    });
                                                    if step == "complete" {
                                                        let _ = app_handle_clone.emit("pipeline-complete", &phase_clone);
                                                    } else if step == "error" {
                                                        let _ = app_handle_clone.emit("pipeline-error", msg);
                                                    }
                                                }
                                            }
                                            last_pos += line.len() as u64 + 1;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                std::thread::sleep(std::time::Duration::from_millis(300));
            }
        });

        let status = {
            let mut child_guard = child_wait.lock().unwrap();
            child_guard.take().map(|mut c| c.wait()).unwrap_or_else(|| {
                Ok(std::process::ExitStatus::from_raw(0))
            })
        };
        let _ = poll_thread.join();
        *PIPELINE_RUNNING.lock().unwrap() = false;

        match status {
            Ok(s) if s.success() => {
                let _ = app_handle.emit("pipeline-progress", PipelineProgress {
                    phase: phase.clone(), step: "complete".to_string(),
                    message: format!("{} phase completed", phase),
                });
                let _ = app_handle.emit("pipeline-complete", &phase);
            }
            Ok(_) => { let _ = app_handle.emit("pipeline-error", "Pipeline exited with error"); }
            Err(e) => { let _ = app_handle.emit("pipeline-error", format!("Process wait error: {}", e)); }
        }

        remove_pid_file(&output_path);
    });

    Ok(())
}

#[tauri::command]
async fn run_full_pipeline(
    output_dir: String,
    app_handle: tauri::AppHandle,
) -> Result<(), String> {
    {
        let mut locked = PIPELINE_RUNNING.lock().unwrap();
        if *locked { return Err("Pipeline already running".to_string()); }
        *locked = true;
    }

    app_handle.emit("pipeline-started", "full").map_err(|e| e.to_string())?;

    let output_path = PathBuf::from(&output_dir);
    if let Err(e) = write_pid_file(&output_path) {
        eprintln!("[Rust] Warning: failed to write PID file: {}", e);
    }

    std::thread::spawn(move || {
        let app_root = find_app_root();
        let python = find_python(&app_root);
        let script = app_root.join("run_pipeline.py");
        let progress_file = output_path.join(".novelforge").join("progress.jsonl");

        let args = vec![
            script.to_string_lossy().to_string(),
            "--full".to_string(),
            "--output-dir".to_string(), output_dir.clone(),
        ];

        let _ = app_handle.emit("pipeline-progress", PipelineProgress {
            phase: "full".to_string(), step: "running".to_string(),
            message: "Running full pipeline...".to_string(),
        });

        let child = match Command::new(&python)
            .env("PYTHONPATH", app_root.to_str().unwrap_or(""))
            .args(&args)
            .current_dir(&app_root)
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                *PIPELINE_RUNNING.lock().unwrap() = false;
                remove_pid_file(&output_path);
                let _ = app_handle.emit("pipeline-error",
                    format!("Failed to start Python ({}): {}", python, e));
                return;
            }
        };

        use std::sync::{Arc, Mutex};
        let child: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(Some(child)));
        let child_poll = child.clone();
        let child_wait = child.clone();

        // File-polling thread: read progress.jsonl and emit events
        let app_handle_clone = app_handle.clone();
        let progress_file_clone = progress_file.clone();
        let poll_thread = std::thread::spawn(move || {
            let mut last_pos = 0u64;
            for _ in 0..50 {
                if progress_file_clone.exists() { break; }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }

            loop {
                let child_guard = child_poll.lock().unwrap();
                if child_guard.is_none() {
                    break;
                }
                drop(child_guard);

                if progress_file_clone.exists() {
                    if let Ok(metadata) = progress_file_clone.metadata() {
                        let current_size = metadata.len();
                        if current_size > last_pos {
                            if let Ok(mut file) = fs::File::open(&progress_file_clone) {
                                use std::io::{Seek, BufRead, BufReader};
                                if file.seek(std::io::SeekFrom::Start(last_pos)).is_ok() {
                                    let reader = BufReader::new(file);
                                    for line_result in reader.lines() {
                                        if let Ok(line) = line_result {
                                            if !line.is_empty() {
                                                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&line) {
                                                    let msg = json.get("message").and_then(|v| v.as_str()).unwrap_or("");
                                                    let step = json.get("step").and_then(|v| v.as_str()).unwrap_or("running");
                                                    let _ = app_handle_clone.emit("pipeline-progress", PipelineProgress {
                                                        phase: "full".to_string(),
                                                        step: step.to_string(),
                                                        message: msg.to_string(),
                                                    });
                                                    if step == "complete" {
                                                        let _ = app_handle_clone.emit("pipeline-complete", "full");
                                                    } else if step == "error" {
                                                        let _ = app_handle_clone.emit("pipeline-error", msg);
                                                    }
                                                }
                                            }
                                            last_pos += line.len() as u64 + 1;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                std::thread::sleep(std::time::Duration::from_millis(300));
            }
        });

        let status = {
            let mut child_guard = child_wait.lock().unwrap();
            child_guard.take().map(|mut c| c.wait()).unwrap_or_else(|| {
                Ok(std::process::ExitStatus::from_raw(0))
            })
        };
        let _ = poll_thread.join();
        *PIPELINE_RUNNING.lock().unwrap() = false;

        match status {
            Ok(s) if s.success() => {
                let _ = app_handle.emit("pipeline-progress", PipelineProgress {
                    phase: "full".to_string(), step: "complete".to_string(),
                    message: "Full pipeline completed".to_string(),
                });
                let _ = app_handle.emit("pipeline-complete", "full");
            }
            Ok(_) => { let _ = app_handle.emit("pipeline-error", "Pipeline exited with error"); }
            Err(e) => { let _ = app_handle.emit("pipeline-error", format!("Process wait error: {}", e)); }
        }

        remove_pid_file(&output_path);
    });

    Ok(())
}

// ─────────────────────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────────────────────

fn extract_title(content: &str) -> Option<String> {
    content.lines()
        .find(|l| l.trim().starts_with("# "))
        .map(|l| l.trim().strip_prefix("# ").unwrap().to_string())
}

fn format_datetime(time: std::time::SystemTime) -> Option<String> {
    let secs = time.duration_since(std::time::UNIX_EPOCH).ok()?.as_secs();
    let days = secs / 86400;
    let rem = secs % 86400;
    let (hour, minutes) = (rem / 3600, (rem % 3600) / 60);
    let (year, yday) = iso_day_of_year(days as i64)?;
    let is_leap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    let dim: [u64; 12] = if is_leap { [31,29,31,30,31,30,31,31,30,31,30,31] }
                         else        { [31,28,31,30,31,30,31,31,30,31,30,31] };
    let mut month = 1u64;
    let mut rem2 = yday;
    for (i, &d) in dim.iter().enumerate() {
        if rem2 < d { month = i as u64 + 1; break; }
        rem2 -= d;
    }
    Some(format!("{:04}-{:02}-{:02} {:02}:{:02}", year, month, rem2 + 1, hour, minutes))
}

fn iso_day_of_year(days: i64) -> Option<(i64, u64)> {
    let mut d = days;
    let mut year = 1970i64;
    if d < 0 { let c = (d + 1) / 146097 - 1; d -= c * 146097; year += c * 400; }
    let c400 = d / 146097; d -= c400 * 146097; year += c400 * 400;
    let c100 = d / 36524;
    if c100 == 4 { d -= 3 * 36524 + 366; year += 300; }
    else { d -= c100 * 36524; year += c100 * 100; }
    let c4 = d / 1461; d -= c4 * 1461; year += c4 * 4;
    let c1 = d / 365;
    if c1 == 4 { year += 3; return Some((year, 365)); }
    d -= c1 * 365; year += c1;
    Some((year, d as u64))
}

fn base64_encode(data: &[u8]) -> String {
    const A: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut r = String::new();
    for chunk in data.chunks(3) {
        let (b0, b1, b2) = (chunk[0] as usize,
                            chunk.get(1).copied().unwrap_or(0) as usize,
                            chunk.get(2).copied().unwrap_or(0) as usize);
        r.push(A[b0 >> 2] as char);
        r.push(A[((b0 & 3) << 4) | (b1 >> 4)] as char);
        r.push(if chunk.len() > 1 { A[((b1 & 0xf) << 2) | (b2 >> 6)] as char } else { '=' });
        r.push(if chunk.len() > 2 { A[b2 & 0x3f] as char } else { '=' });
    }
    r
}

// ─────────────────────────────────────────────────────────────────────────────
// Tauri entry point
// ─────────────────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_project_path,
            read_seed,
            read_language,
            write_seed,
            reset_project_state,
            read_ai_config,
            write_ai_config,
            generate_title,
            read_state,
            read_chapter,
            read_foundation_doc,
            check_pipeline_status,
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
