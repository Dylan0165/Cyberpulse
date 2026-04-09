#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

struct SidecarState(Mutex<Option<Child>>);

fn start_python_backend() -> Option<Child> {
    // Try to start the FastAPI backend as a sidecar process
    let child = Command::new("python")
        .args(["-m", "uvicorn", "web.app:app", "--host", "127.0.0.1", "--port", "7823"])
        .current_dir(
            std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|p| p.to_path_buf()))
                .and_then(|p| {
                    // In dev: exe is at target/debug/, so ../../../ = cyberpulse root
                    let engine_dir = p.join("../../../");
                    if engine_dir.join("web").exists() {
                        Some(engine_dir)
                    } else {
                        // Fallback: check CYBERPULSE_ENGINE_DIR env var
                        std::env::var("CYBERPULSE_ENGINE_DIR")
                            .ok()
                            .map(std::path::PathBuf::from)
                    }
                })
                .unwrap_or_else(|| std::path::PathBuf::from(".")),
        )
        .spawn()
        .ok();

    if child.is_some() {
        println!("[CyberPulse] Python backend started on port 7823");
    } else {
        eprintln!("[CyberPulse] Failed to start Python backend");
    }

    child
}

#[tauri::command]
fn get_engine_status() -> String {
    // Check if the engine is reachable
    match std::net::TcpStream::connect_timeout(
        &"127.0.0.1:7823".parse().unwrap(),
        std::time::Duration::from_millis(500),
    ) {
        Ok(_) => "online".to_string(),
        Err(_) => "offline".to_string(),
    }
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start Python backend as sidecar
            let child = start_python_backend();
            app.manage(SidecarState(Mutex::new(child)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_engine_status])
        .on_window_event(|event| {
            if let tauri::WindowEvent::Destroyed = event.event() {
                // Kill the Python backend when the window closes
                let app_handle = event.window().app_handle();
                if let Some(state) = app_handle.try_state::<SidecarState>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(ref mut child) = *guard {
                            let _ = child.kill();
                            println!("[CyberPulse] Python backend stopped");
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error running CyberPulse");
}
