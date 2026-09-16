use std::fs;
use std::env;

#[repr(C)]
#[derive(Debug, Clone, Copy)]
struct DemoState {
    id: i32,
    value: f32,
    label: [u8; 32],
}

fn read_state(path: &str) -> Result<DemoState, Box<dyn std::error::Error>> {
    let data = fs::read(path)?;
    if data.len() != 40 { return Err("Invalid size".into()); }
    let mut s = DemoState { id: 0, value: 0.0, label: [0; 32] };
    s.id = i32::from_le_bytes([data[0], data[1], data[2], data[3]]);
    s.value = f32::from_le_bytes([data[4], data[5], data[6], data[7]]);
    s.label.copy_from_slice(&data[8..40]);
    Ok(s)
}

fn write_state(path: &str, s: &DemoState) -> Result<(), Box<dyn std::error::Error>> {
    let mut data = Vec::with_capacity(40);
    data.extend_from_slice(&s.id.to_le_bytes());
    data.extend_from_slice(&s.value.to_le_bytes());
    data.extend_from_slice(&s.label);
    fs::write(path, data)?;
    Ok(())
}

fn label_str(label: &[u8; 32]) -> String {
    let end = label.iter().position(|&b| b == 0).unwrap_or(32);
    String::from_utf8_lossy(&label[..end]).into_owned()
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    let default_json = "/tmp/swuir_session.json".to_string();
    let default_state = "/tmp/swuir_session_state.bin".to_string();
    let default_out = "/tmp/swuir_session_state_rust.bin".to_string();
    
    let json_file = args.get(1).unwrap_or(&default_json);
    let state_file = args.get(2).unwrap_or(&default_state);
    let out_file = args.get(3).unwrap_or(&default_out);
    
    println!("[Rust Session] Reading IL from {}", json_file);
    println!("[Rust Session] Reading state from {}", state_file);
    
    let mut state = read_state(state_file)?;
    println!("[Rust Session] Parsed: ID={}, Value={:.2}, Label={}", 
             state.id, state.value, label_str(&state.label));
    
    println!("[Rust Session] Executing Rust warp...");
    state.value *= 2.0;
    state.label = {
        let mut l = [0u8; 32];
        let s = format!("RUST_{}", label_str(&state.label));
        let bytes = s.as_bytes();
        let len = bytes.len().min(31);
        l[..len].copy_from_slice(&bytes[..len]);
        l
    };
    
    println!("[Rust Session] After warp: Value={:.2}, Label={}", 
             state.value, label_str(&state.label));
    
    write_state(out_file, &state)?;
    println!("[Rust Session] Wrote modified state to {}", out_file);
    Ok(())
}