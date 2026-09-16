use libc::{c_char, c_void, size_t, c_int};
use std::ffi::{CStr, CString};
use std::fs;
use std::os::raw::c_void as RawCVoid;

pub const SWUIR_IL_VERSION: u32 = 1;

#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SwuirILType {
    Void = 0, I8 = 1, I16 = 2, I32 = 3, I64 = 4,
    U8 = 5, U16 = 6, U32 = 7, U64 = 8,
    F32 = 9, F64 = 10, Bool = 11, String = 12,
    Pointer = 13, Struct = 14, Array = 15,
}

#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SwuirILSessionStatus {
    Pending = 0, Running = 1, Completed = 2, Failed = 3,
}

#[repr(C)]
#[derive(Debug, Clone)]
pub struct SwuirILField {
    pub name: [c_char; 256],
    pub type_: SwuirILType,
    pub value_u64: u64, pub value_i64: i64, pub value_f64: f64,
    pub value_str: [c_char; 256],
    pub array_len: size_t, pub struct_field_count: size_t, pub offset: size_t,
}

#[repr(C)]
#[derive(Debug, Clone)]
pub struct SwuirILTypeDef {
    pub name: [c_char; 256],
    pub fields: [SwuirILField; 32],
    pub field_count: size_t, pub total_size: size_t,
}

#[repr(C)]
#[derive(Debug, Clone)]
pub struct SwuirILSession {
    pub target_func: [c_char; 256],
    pub state_type: [c_char; 256],
    pub state_data: *mut c_void, pub state_size: size_t,
    pub status: SwuirILSessionStatus, pub session_id: u64,
}

#[repr(C)]
#[derive(Debug)]
pub struct SwuirILModule {
    pub version: u32, pub magic: u32,
    pub module_name: [c_char; 256],
    pub types: [SwuirILTypeDef; 32], pub type_count: size_t,
    pub sessions: [SwuirILSession; 64], pub session_count: size_t,
    pub memory_pool: *mut c_void, pub pool_size: size_t, pub pool_used: size_t,
}

extern "C" {
    fn swuir_il_module_create(module_name: *const c_char, pool_size: size_t) -> *mut SwuirILModule;
    fn swuir_il_module_destroy(module: *mut SwuirILModule);
    fn swuir_il_add_session(module: *mut SwuirILModule, target_func: *const c_char, state_type: *const c_char, state_data: *const c_void, state_size: size_t) -> c_int;
    fn swuir_il_serialize_json(module: *mut SwuirILModule) -> *mut c_char;
    fn swuir_il_get_state_data(module: *mut SwuirILModule, session_id: u64, out_size: *mut size_t) -> *mut c_void;
    fn swuir_il_set_session_status(module: *mut SwuirILModule, session_id: u64, status: SwuirILSessionStatus) -> c_int;
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct DemoState {
    pub id: i32,
    pub value: f32,
    pub label: [u8; 32],
}

fn read_state_file(path: &str) -> Result<DemoState, Box<dyn std::error::Error>> {
    let data = fs::read(path)?;
    if data.len() != 40 {
        return Err("Invalid state file size".into());
    }
    let mut state = DemoState { id: 0, value: 0.0, label: [0; 32] };
    state.id = i32::from_le_bytes([data[0], data[1], data[2], data[3]]);
    state.value = f32::from_le_bytes([data[4], data[5], data[6], data[7]]);
    state.label.copy_from_slice(&data[8..40]);
    Ok(state)
}

fn write_state_file(path: &str, state: &DemoState) -> Result<(), Box<dyn std::error::Error>> {
    let mut data = Vec::with_capacity(40);
    data.extend_from_slice(&state.id.to_le_bytes());
    data.extend_from_slice(&state.value.to_le_bytes());
    data.extend_from_slice(&state.label);
    fs::write(path, data)?;
    Ok(())
}

fn label_to_str(label: &[u8; 32]) -> String {
    let end = label.iter().position(|&b| b == 0).unwrap_or(32);
    String::from_utf8_lossy(&label[..end]).into_owned()
}

fn str_to_label(s: &str) -> [u8; 32] {
    let mut label = [0u8; 32];
    let bytes = s.as_bytes();
    let len = bytes.len().min(31);
    label[..len].copy_from_slice(&bytes[..len]);
    label
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: {} <json_file> <input_state_file> <output_state_file>", args[0]);
        std::process::exit(1);
    }
    
    let json_file = &args[1];
    let input_state = &args[2];
    let output_state = &args[3];
    
    println!("[RUST EXECUTOR] Loading state from {}", input_state);
    let mut state = read_state_file(input_state)?;
    println!("[RUST EXECUTOR] Parsed state: ID={}, Value={:.2}, Label={}", 
             state.id, state.value, label_to_str(&state.label));
    
    println!("[RUST EXECUTOR] Executing Rust warp session...");
    println!("[RUST EXECUTOR] Modifying state in Rust warp...");
    
    state.value *= 2.0;
    state.label = str_to_label(&format!("RUST_{}", label_to_str(&state.label)));
    
    println!("[RUST EXECUTOR] State after Rust warp: Value={:.2}, Label={}", 
             state.value, label_to_str(&state.label));
    
    write_state_file(output_state, &state)?;
    println!("[RUST EXECUTOR] Saved modified state to {}", output_state);
    
    Ok(())
}