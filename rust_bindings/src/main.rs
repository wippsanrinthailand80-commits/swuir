use libc::{c_char, c_void, size_t, c_int};
use std::ffi::{CStr, CString};

pub const SWUIR_IL_VERSION: u32 = 1;
pub const SWUIR_IL_MAX_STRING: usize = 256;
pub const SWUIR_IL_MAX_FIELDS: usize = 32;
pub const SWUIR_IL_MAX_SESSIONS: usize = 64;
pub const SWUIR_IL_MAGIC: u32 = 0x53575549;

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
    pub name: [c_char; SWUIR_IL_MAX_STRING],
    pub type_: SwuirILType,
    pub value_u64: u64, pub value_i64: i64, pub value_f64: f64,
    pub value_str: [c_char; SWUIR_IL_MAX_STRING],
    pub array_len: size_t, pub struct_field_count: size_t, pub offset: size_t,
}

#[repr(C)]
#[derive(Debug, Clone)]
pub struct SwuirILTypeDef {
    pub name: [c_char; SWUIR_IL_MAX_STRING],
    pub fields: [SwuirILField; SWUIR_IL_MAX_FIELDS],
    pub field_count: size_t, pub total_size: size_t,
}

#[repr(C)]
#[derive(Debug, Clone)]
pub struct SwuirILSession {
    pub target_func: [c_char; SWUIR_IL_MAX_STRING],
    pub state_type: [c_char; SWUIR_IL_MAX_STRING],
    pub state_data: *mut c_void, pub state_size: size_t,
    pub status: SwuirILSessionStatus, pub session_id: u64,
}

#[repr(C)]
#[derive(Debug)]
pub struct SwuirILModule {
    pub version: u32, pub magic: u32,
    pub module_name: [c_char; SWUIR_IL_MAX_STRING],
    pub types: [SwuirILTypeDef; SWUIR_IL_MAX_FIELDS], pub type_count: size_t,
    pub sessions: [SwuirILSession; SWUIR_IL_MAX_SESSIONS], pub session_count: size_t,
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

#[derive(Debug)]
pub enum SwuirILError {
    ModuleCreationFailed, SessionCreationFailed, SerializationFailed,
    InvalidSessionId, NulError(std::ffi::NulError),
}

impl From<std::ffi::NulError> for SwuirILError {
    fn from(e: std::ffi::NulError) -> Self { SwuirILError::NulError(e) }
}

impl std::fmt::Display for SwuirILError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SwuirILError::ModuleCreationFailed => write!(f, "Failed to create module"),
            SwuirILError::SessionCreationFailed => write!(f, "Failed to add session"),
            SwuirILError::SerializationFailed => write!(f, "Serialization failed"),
            SwuirILError::InvalidSessionId => write!(f, "Invalid session ID"),
            SwuirILError::NulError(e) => write!(f, "NUL byte in string: {}", e),
        }
    }
}

impl std::error::Error for SwuirILError {}

pub struct SwuirILModuleWrapper {
    ptr: *mut SwuirILModule,
}

impl SwuirILModuleWrapper {
    pub fn new(module_name: &str, pool_size: usize) -> Result<Self, SwuirILError> {
        let name = CString::new(module_name)?;
        let ptr = unsafe { swuir_il_module_create(name.as_ptr(), pool_size) };
        if ptr.is_null() { return Err(SwuirILError::ModuleCreationFailed); }
        Ok(Self { ptr })
    }
    
    pub fn add_session(&self, target_func: &str, state_type: &str, state_data: &[u8]) -> Result<u64, SwuirILError> {
        let target = CString::new(target_func)?; let stype = CString::new(state_type)?;
        let result = unsafe { swuir_il_add_session(self.ptr, target.as_ptr(), stype.as_ptr(), state_data.as_ptr() as *const c_void, state_data.len()) };
        if result != 0 { return Err(SwuirILError::SessionCreationFailed); }
        let session = unsafe { &(*self.ptr).sessions[(*self.ptr).session_count - 1] };
        Ok(session.session_id)
    }
    
    pub fn serialize_json(&self) -> Result<String, SwuirILError> {
        let json_ptr = unsafe { swuir_il_serialize_json(self.ptr) };
        if json_ptr.is_null() { return Err(SwuirILError::SerializationFailed); }
        let cstr = unsafe { CStr::from_ptr(json_ptr) };
        let result = cstr.to_string_lossy().into_owned();
        unsafe { libc::free(json_ptr as *mut c_void) };
        Ok(result)
    }
    
    pub fn get_state_data(&self, session_id: u64) -> Result<Vec<u8>, SwuirILError> {
        let mut size: size_t = 0;
        let ptr = unsafe { swuir_il_get_state_data(self.ptr, session_id, &mut size) };
        if ptr.is_null() || size == 0 { return Err(SwuirILError::InvalidSessionId); }
        let slice = unsafe { std::slice::from_raw_parts(ptr as *const u8, size) };
        Ok(slice.to_vec())
    }
    
    pub fn set_session_status(&self, session_id: u64, status: SwuirILSessionStatus) -> Result<(), SwuirILError> {
        let result = unsafe { swuir_il_set_session_status(self.ptr, session_id, status) };
        if result != 0 { return Err(SwuirILError::InvalidSessionId); }
        Ok(())
    }
}

impl Drop for SwuirILModuleWrapper { fn drop(&mut self) { if !self.ptr.is_null() { unsafe { swuir_il_module_destroy(self.ptr) }; } } }

fn create_demo_state() -> Vec<u8> {
    let mut data = Vec::new();
    data.extend_from_slice(&42i32.to_le_bytes());
    data.extend_from_slice(&3.14f32.to_le_bytes());
    let mut label = [0u8; 32]; label[..13].copy_from_slice(b"INITIAL_STATE");
    data.extend_from_slice(&label); data
}

fn main() -> Result<(), SwuirILError> {
    println!("[Rust] Creating S.W.UIR IL context...");
    let ctx = SwuirILModuleWrapper::new("rust_demo", 1024 * 1024)?;
    println!("[Rust] Creating initial state...");
    let state_data = create_demo_state();
    println!("[Rust] State data: {:02x?}", state_data);
    println!("[Rust] Adding warp session targeting 'dormant_block_target'...");
    let session_id = ctx.add_session("dormant_block_target", "DemoState", &state_data)?;
    println!("[Rust] Session created with ID: {:#018X}", session_id);
    println!("[Rust] Serializing to JSON...");
    let json = ctx.serialize_json()?; println!("{}", json);
    println!("[Rust] Demo complete!"); Ok(())
}