use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq)]
#[repr(u8)]
pub enum VMOpcode {
    NOP = 0x00,
    PUSH_I32 = 0x10,
    PUSH_I64 = 0x11,
    PUSH_F32 = 0x12,
    PUSH_F64 = 0x13,
    POP = 0x14,
    DUP = 0x15,
    SWAP = 0x16,
    ADD = 0x20,
    SUB = 0x21,
    MUL = 0x22,
    DIV = 0x23,
    MOD = 0x24,
    NEG = 0x25,
    EQ = 0x30,
    NE = 0x31,
    LT = 0x32,
    LE = 0x33,
    GT = 0x34,
    GE = 0x35,
    AND = 0x38,
    OR = 0x39,
    NOT = 0x3A,
    JMP = 0x40,
    JMP_IF = 0x41,
    JMP_IF_NOT = 0x42,
    CALL = 0x43,
    RET = 0x44,
    LOAD = 0x50,
    STORE = 0x51,
    LOAD_GLOBAL = 0x52,
    STORE_GLOBAL = 0x53,
    PRINT = 0x60,
    PRINTLN = 0x61,
    WARP = 0x70,
    JOIN = 0x71,
    HALT = 0xFF,
}

#[derive(Debug, Clone, Copy, PartialEq)]
#[repr(u8)]
pub enum VMValueType {
    I32 = 1,
    I64 = 2,
    F32 = 3,
    F64 = 4,
    PTR = 5,
}

#[derive(Clone)]
pub enum VMValue {
    I32(i32),
    I64(i64),
    F32(f32),
    F64(f64),
    Ptr(*mut std::ffi::c_void),
}

impl fmt::Debug for VMValue {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            VMValue::I32(v) => write!(f, "I32({})", v),
            VMValue::I64(v) => write!(f, "I64({})", v),
            VMValue::F32(v) => write!(f, "F32({})", v),
            VMValue::F64(v) => write!(f, "F64({})", v),
            VMValue::Ptr(p) => write!(f, "Ptr({:p})", p),
        }
    }
}

impl VMValue {
    pub fn as_i32(&self) -> Option<i32> {
        match self { VMValue::I32(v) => Some(*v), _ => None }
    }
    pub fn as_i64(&self) -> Option<i64> {
        match self { VMValue::I64(v) => Some(*v), _ => None }
    }
    pub fn as_f32(&self) -> Option<f32> {
        match self { VMValue::F32(v) => Some(*v), _ => None }
    }
    pub fn as_f64(&self) -> Option<f64> {
        match self { VMValue::F64(v) => Some(*v), _ => None }
    }
}

#[derive(Debug, Clone)]
pub struct VMStackValue {
    pub value_type: VMValueType,
    pub value: VMValue,
}

impl VMStackValue {
    pub fn i32(v: i32) -> Self {
        VMStackValue { value_type: VMValueType::I32, value: VMValue::I32(v) }
    }
    pub fn i64(v: i64) -> Self {
        VMStackValue { value_type: VMValueType::I64, value: VMValue::I64(v) }
    }
    pub fn f32(v: f32) -> Self {
        VMStackValue { value_type: VMValueType::F32, value: VMValue::F32(v) }
    }
    pub fn f64(v: f64) -> Self {
        VMStackValue { value_type: VMValueType::F64, value: VMValue::F64(v) }
    }
}

#[derive(Debug)]
pub struct VMContext {
    bytecode: Vec<u8>,
    pc: usize,
    stack: Vec<VMStackValue>,
    globals: Vec<VMStackValue>,
    halted: bool,
    error: Option<String>,
}

impl VMContext {
    pub fn new(bytecode: Vec<u8>) -> Self {
        VMContext {
            bytecode,
            pc: 0,
            stack: Vec::new(),
            globals: Vec::new(),
            halted: false,
            error: None,
        }
    }
    
    fn push_i32(&mut self, v: i32) {
        self.stack.push(VMStackValue { value_type: VMValueType::I32, value: VMValue::I32(v) });
    }
    fn push_i64(&mut self, v: i64) {
        self.stack.push(VMStackValue { value_type: VMValueType::I64, value: VMValue::I64(v) });
    }
    fn push_f32(&mut self, v: f32) {
        self.stack.push(VMStackValue { value_type: VMValueType::F32, value: VMValue::F32(v) });
    }
    fn push_f64(&mut self, v: f64) {
        self.stack.push(VMStackValue { value_type: VMValueType::F64, value: VMValue::F64(v) });
    }
    fn pop(&mut self) -> Result<VMStackValue, String> {
        self.stack.pop().ok_or("Stack underflow".to_string())
    }
    fn peek(&self) -> Result<&VMStackValue, String> {
        self.stack.last().ok_or("Stack empty".to_string())
    }
    fn ensure_globals(&mut self, idx: usize) {
        while self.globals.len() <= idx {
            self.globals.push(VMStackValue::i32(0));
        }
    }
    
    fn read_i32(&mut self) -> Result<i32, String> {
        if self.pc + 4 > self.bytecode.len() {
            return Err("Truncated i32".to_string());
        }
        let bytes: [u8; 4] = self.bytecode[self.pc..self.pc+4].try_into().unwrap();
        self.pc += 4;
        Ok(i32::from_le_bytes(bytes))
    }
    fn read_i64(&mut self) -> Result<i64, String> {
        if self.pc + 8 > self.bytecode.len() {
            return Err("Truncated i64".to_string());
        }
        let bytes: [u8; 8] = self.bytecode[self.pc..self.pc+8].try_into().unwrap();
        self.pc += 8;
        Ok(i64::from_le_bytes(bytes))
    }
    fn read_f32(&mut self) -> Result<f32, String> {
        if self.pc + 4 > self.bytecode.len() {
            return Err("Truncated f32".to_string());
        }
        let bytes: [u8; 4] = self.bytecode[self.pc..self.pc+4].try_into().unwrap();
        self.pc += 4;
        Ok(f32::from_le_bytes(bytes))
    }
    fn read_f64(&mut self) -> Result<f64, String> {
        if self.pc + 8 > self.bytecode.len() {
            return Err("Truncated f64".to_string());
        }
        let bytes: [u8; 8] = self.bytecode[self.pc..self.pc+8].try_into().unwrap();
        self.pc += 8;
        Ok(f64::from_le_bytes(bytes))
    }
    
    fn binary_op_i32(&mut self, opcode: VMOpcode, av: i32, bv: i32) -> Result<i32, String> {
        Ok(match opcode {
            VMOpcode::ADD => av + bv,
            VMOpcode::SUB => av - bv,
            VMOpcode::MUL => av * bv,
            VMOpcode::DIV => if bv != 0 { av / bv } else { 0 },
            VMOpcode::MOD => if bv != 0 { av % bv } else { 0 },
            VMOpcode::EQ => (av == bv) as i32,
            VMOpcode::NE => (av != bv) as i32,
            VMOpcode::LT => (av < bv) as i32,
            VMOpcode::LE => (av <= bv) as i32,
            VMOpcode::GT => (av > bv) as i32,
            VMOpcode::GE => (av >= bv) as i32,
            VMOpcode::AND => ((av != 0 && bv != 0) as i32),
            VMOpcode::OR => ((av != 0 || bv != 0) as i32),
            _ => return Err("Invalid binary opcode for i32".to_string()),
        })
    }
    
    fn binary_op_f64(&mut self, opcode: VMOpcode, av: f64, bv: f64) -> Result<f64, String> {
        Ok(match opcode {
            VMOpcode::ADD => av + bv,
            VMOpcode::SUB => av - bv,
            VMOpcode::MUL => av * bv,
            VMOpcode::DIV => if bv != 0.0 { av / bv } else { 0.0 },
            VMOpcode::EQ => (av == bv) as i32 as f64,
            VMOpcode::NE => (av != bv) as i32 as f64,
            VMOpcode::LT => (av < bv) as i32 as f64,
            VMOpcode::LE => (av <= bv) as i32 as f64,
            VMOpcode::GT => (av > bv) as i32 as f64,
            VMOpcode::GE => (av >= bv) as i32 as f64,
            _ => return Err("Invalid binary opcode for float".to_string()),
        })
    }
    
    fn unary_op(&mut self, opcode: VMOpcode) -> Result<(), String> {
        let a = self.pop()?;
        match a.value_type {
            VMValueType::I32 => {
                let av = match a.value { VMValue::I32(v) => v, _ => unreachable!() };
                let res = match opcode {
                    VMOpcode::NEG => -av,
                    VMOpcode::NOT => (av == 0) as i32,
                    _ => return Err("Invalid unary opcode for i32".to_string()),
                };
                self.push_i32(res);
            }
            VMValueType::F32 => {
                let av = match a.value { VMValue::F32(v) => v as f64, _ => unreachable!() };
                let res = match opcode {
                    VMOpcode::NEG => -av,
                    _ => return Err("Invalid unary opcode for float".to_string()),
                };
                self.push_f64(res);
            }
            VMValueType::F64 => {
                let av = match a.value { VMValue::F64(v) => v, _ => unreachable!() };
                let res = match opcode {
                    VMOpcode::NEG => -av,
                    _ => return Err("Invalid unary opcode for float".to_string()),
                };
                self.push_f64(res);
            }
            _ => return Err("Type mismatch in unary op".to_string()),
        }
        Ok(())
    }
    
    pub fn execute(&mut self) -> Result<(), String> {
        while !self.halted && self.pc < self.bytecode.len() {
            self.step()?;
        }
        Ok(())
    }
    
    pub fn step(&mut self) -> Result<bool, String> {
        if self.pc >= self.bytecode.len() {
            return Err("PC out of bounds".to_string());
        }
        
        let opcode = match VMOpcode::from_u8(self.bytecode[self.pc]) {
            Some(o) => o,
            None => return Err(format!("Unknown opcode: {:02x}", self.bytecode[self.pc])),
        };
        self.pc += 1;
        
        match opcode {
            VMOpcode::NOP => {}
            VMOpcode::PUSH_I32 => { let v = self.read_i32()?; self.push_i32(v); }
            VMOpcode::PUSH_I64 => { let v = self.read_i64()?; self.push_i64(v); }
            VMOpcode::PUSH_F32 => { let v = self.read_f32()?; self.push_f32(v); }
            VMOpcode::PUSH_F64 => { let v = self.read_f64()?; self.push_f64(v); }
            VMOpcode::POP => { self.pop()?; }
            VMOpcode::DUP => {
                let v = self.peek()?.clone();
                self.stack.push(v);
            }
            VMOpcode::SWAP => {
                if self.stack.len() < 2 { return Err("SWAP: need 2 values".to_string()); }
                let len = self.stack.len();
                self.stack.swap(len - 1, len - 2);
            }
            VMOpcode::ADD | VMOpcode::SUB | VMOpcode::MUL | VMOpcode::DIV | VMOpcode::MOD
            | VMOpcode::EQ | VMOpcode::NE | VMOpcode::LT | VMOpcode::LE | VMOpcode::GT | VMOpcode::GE
            | VMOpcode::AND | VMOpcode::OR => {
                let b = self.pop()?;
                let a = self.pop()?;
                
                match (a.value_type, b.value_type) {
                    (VMValueType::I32, VMValueType::I32) => {
                        let av = match a.value { VMValue::I32(v) => v, _ => unreachable!() };
                        let bv = match b.value { VMValue::I32(v) => v, _ => unreachable!() };
                        let res = self.binary_op_i32(opcode, av, bv)?;
                        self.push_i32(res);
                    }
                    (VMValueType::F32, VMValueType::F32) |
                    (VMValueType::F32, VMValueType::F64) |
                    (VMValueType::F64, VMValueType::F32) |
                    (VMValueType::F64, VMValueType::F64) => {
                        let av = match a.value { VMValue::F32(v) => v as f64, VMValue::F64(v) => v, _ => unreachable!() };
                        let bv = match b.value { VMValue::F32(v) => v as f64, VMValue::F64(v) => v, _ => unreachable!() };
                        let res = self.binary_op_f64(opcode, av, bv)?;
                        self.push_f64(res);
                    }
                    _ => return Err("Type mismatch in binary op".to_string()),
                }
            }
            VMOpcode::NEG | VMOpcode::NOT => {
                self.unary_op(opcode)?;
            }
            VMOpcode::JMP => {
                let offset = self.read_i32()?;
                self.pc = offset as usize;
            }
            VMOpcode::JMP_IF => {
                let offset = self.read_i32()?;
                let cond = self.pop()?;
                if let VMValue::I32(v) = cond.value {
                    if v != 0 { self.pc = offset as usize; }
                } else { return Err("JMP_IF: condition must be i32".to_string()); }
            }
            VMOpcode::JMP_IF_NOT => {
                let offset = self.read_i32()?;
                let cond = self.pop()?;
                if let VMValue::I32(v) = cond.value {
                    if v == 0 { self.pc = offset as usize; }
                } else { return Err("JMP_IF_NOT: condition must be i32".to_string()); }
            }
            VMOpcode::CALL => {
                let addr = self.read_i32()?;
                self.push_i32(self.pc as i32);
                self.pc = addr as usize;
            }
            VMOpcode::RET => {
                let ret_addr = self.pop()?;
                if let VMValue::I32(v) = ret_addr.value {
                    self.pc = v as usize;
                } else { return Err("RET: invalid return address".to_string()); }
            }
            VMOpcode::LOAD => {
                let idx = self.pop()?;
                if let VMValue::I32(v) = idx.value {
                    let i = v as usize;
                    if i < self.globals.len() {
                        self.stack.push(self.globals[i].clone());
                    } else { return Err("LOAD: invalid global index".to_string()); }
                } else { return Err("LOAD: invalid index type".to_string()); }
            }
            VMOpcode::STORE => {
                let idx = self.pop()?;
                let val = self.pop()?;
                if let VMValue::I32(v) = idx.value {
                    let i = v as usize;
                    if v >= 0 { self.ensure_globals(i); self.globals[i] = val; }
                    else { return Err("STORE: invalid index".to_string()); }
                } else { return Err("STORE: invalid index type".to_string()); }
            }
            VMOpcode::LOAD_GLOBAL => {
                let idx = self.read_i32()?;
                if idx >= 0 && (idx as usize) < self.globals.len() {
                    self.stack.push(self.globals[idx as usize].clone());
                } else { return Err("LOAD_GLOBAL: invalid index".to_string()); }
            }
            VMOpcode::STORE_GLOBAL => {
                let idx = self.read_i32()?;
                let val = self.pop()?;
                if idx >= 0 {
                    let i = idx as usize;
                    self.ensure_globals(i);
                    self.globals[i] = val;
                } else { return Err("STORE_GLOBAL: invalid index".to_string()); }
            }
            VMOpcode::PRINT => {
                let v = self.pop()?;
                match v.value_type {
                    VMValueType::I32 => print!("{}", match v.value { VMValue::I32(x) => x, _ => unreachable!() }),
                    VMValueType::I64 => print!("{}", match v.value { VMValue::I64(x) => x, _ => unreachable!() }),
                    VMValueType::F32 => print!("{}", match v.value { VMValue::F32(x) => x, _ => unreachable!() }),
                    VMValueType::F64 => print!("{}", match v.value { VMValue::F64(x) => x, _ => unreachable!() }),
                    _ => print!("<unknown>"),
                }
            }
            VMOpcode::PRINTLN => {
                let v = self.pop()?;
                match v.value_type {
                    VMValueType::I32 => println!("{}", match v.value { VMValue::I32(x) => x, _ => unreachable!() }),
                    VMValueType::I64 => println!("{}", match v.value { VMValue::I64(x) => x, _ => unreachable!() }),
                    VMValueType::F32 => println!("{}", match v.value { VMValue::F32(x) => x, _ => unreachable!() }),
                    VMValueType::F64 => println!("{}", match v.value { VMValue::F64(x) => x, _ => unreachable!() }),
                    _ => println!(),
                }
            }
            VMOpcode::HALT => {
                self.halted = true;
            }
            _ => return Err(format!("Unknown opcode: {:02x}", opcode as u8)),
        }
        Ok(!self.halted)
    }
}

impl VMOpcode {
    fn from_u8(v: u8) -> Option<Self> {
        match v {
            0x00 => Some(VMOpcode::NOP), 0x10 => Some(VMOpcode::PUSH_I32),
            0x11 => Some(VMOpcode::PUSH_I64), 0x12 => Some(VMOpcode::PUSH_F32),
            0x13 => Some(VMOpcode::PUSH_F64), 0x14 => Some(VMOpcode::POP),
            0x15 => Some(VMOpcode::DUP), 0x16 => Some(VMOpcode::SWAP),
            0x20 => Some(VMOpcode::ADD), 0x21 => Some(VMOpcode::SUB),
            0x22 => Some(VMOpcode::MUL), 0x23 => Some(VMOpcode::DIV),
            0x24 => Some(VMOpcode::MOD), 0x25 => Some(VMOpcode::NEG),
            0x30 => Some(VMOpcode::EQ), 0x31 => Some(VMOpcode::NE),
            0x32 => Some(VMOpcode::LT), 0x33 => Some(VMOpcode::LE),
            0x34 => Some(VMOpcode::GT), 0x35 => Some(VMOpcode::GE),
            0x38 => Some(VMOpcode::AND), 0x39 => Some(VMOpcode::OR),
            0x3A => Some(VMOpcode::NOT), 0x40 => Some(VMOpcode::JMP),
            0x41 => Some(VMOpcode::JMP_IF), 0x42 => Some(VMOpcode::JMP_IF_NOT),
            0x43 => Some(VMOpcode::CALL), 0x44 => Some(VMOpcode::RET),
            0x50 => Some(VMOpcode::LOAD), 0x51 => Some(VMOpcode::STORE),
            0x52 => Some(VMOpcode::LOAD_GLOBAL), 0x53 => Some(VMOpcode::STORE_GLOBAL),
            0x60 => Some(VMOpcode::PRINT), 0x61 => Some(VMOpcode::PRINTLN),
            0x70 => Some(VMOpcode::WARP), 0x71 => Some(VMOpcode::JOIN),
            0xFF => Some(VMOpcode::HALT), _ => None,
        }
    }
}

pub fn serialize_bytecode(bytecode: &[u8]) -> String {
    format!("{{\"bytecode\": \"{}\", \"size\": {}}}", hex::encode(bytecode), bytecode.len())
}

pub fn deserialize_bytecode(json: &str) -> Result<Vec<u8>, serde_json::Error> {
    #[derive(serde::Deserialize)]
    struct BytecodeJson { bytecode: String, size: usize }
    let data: BytecodeJson = serde_json::from_str(json)?;
    Ok(hex::decode(data.bytecode).unwrap_or_default())
}

pub struct BytecodeBuilder { code: Vec<u8> }

impl BytecodeBuilder {
    pub fn new() -> Self { BytecodeBuilder { code: Vec::new() } }
    pub fn emit(&mut self, opcode: VMOpcode) { self.code.push(opcode as u8); }
    pub fn emit_i32(&mut self, v: i32) { self.code.extend_from_slice(&v.to_le_bytes()); }
    pub fn emit_i64(&mut self, v: i64) { self.code.extend_from_slice(&v.to_le_bytes()); }
    pub fn emit_f32(&mut self, v: f32) { self.code.extend_from_slice(&v.to_le_bytes()); }
    pub fn emit_f64(&mut self, v: f64) { self.code.extend_from_slice(&v.to_le_bytes()); }
    
    pub fn push_i32(&mut self, v: i32) { self.emit(VMOpcode::PUSH_I32); self.emit_i32(v); }
    pub fn push_f64(&mut self, v: f64) { self.emit(VMOpcode::PUSH_F64); self.emit_f64(v); }
    pub fn add(&mut self) { self.emit(VMOpcode::ADD); }
    pub fn mul(&mut self) { self.emit(VMOpcode::MUL); }
    pub fn println(&mut self) { self.emit(VMOpcode::PRINTLN); }
    pub fn halt(&mut self) { self.emit(VMOpcode::HALT); }
    pub fn jmp(&mut self, offset: i32) { self.emit(VMOpcode::JMP); self.emit_i32(offset); }
    pub fn jmp_if(&mut self, offset: i32) { self.emit(VMOpcode::JMP_IF); self.emit_i32(offset); }
    pub fn store_global(&mut self, idx: i32) { self.emit(VMOpcode::STORE_GLOBAL); self.emit_i32(idx); }
    pub fn load_global(&mut self, idx: i32) { self.emit(VMOpcode::LOAD_GLOBAL); self.emit_i32(idx); }
    pub fn build(self) -> Vec<u8> { self.code }
}

pub fn create_factorial_bytecode() -> Vec<u8> {
    let mut b = BytecodeBuilder::new();
    b.push_i32(5); b.store_global(0);
    b.push_i32(1); b.store_global(1);
    let loop_start = b.code.len();
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode::SUB); b.store_global(0);
    b.load_global(1); b.load_global(0); b.emit(VMOpcode::MUL); b.store_global(1);
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode::GT);
    b.jmp_if(loop_start as i32);
    b.load_global(1); b.println(); b.halt();
    b.build()
}

pub fn create_fibonacci_bytecode() -> Vec<u8> {
    let mut b = BytecodeBuilder::new();
    b.push_i32(10); b.store_global(0);
    b.push_i32(0); b.store_global(1);
    b.push_i32(1); b.store_global(2);
    let loop_start = b.code.len();
    b.load_global(0); b.push_i32(1); b.emit(VMOpcode::SUB); b.store_global(0);
    b.load_global(1); b.load_global(2); b.emit(VMOpcode::ADD);
    b.load_global(2); b.store_global(1);
    b.store_global(2);
    b.load_global(0); b.push_i32(0); b.emit(VMOpcode::GT);
    b.jmp_if(loop_start as i32);
    b.load_global(2); b.println(); b.halt();
    b.build()
}

fn main() {
    println!("Testing Rust VM...");
    
    let bc = create_factorial_bytecode();
    println!("Factorial bytecode: {}", hex::encode(&bc));
    let mut vm = VMContext::new(bc.clone());
    match vm.execute() {
        Ok(_) => println!("Factorial VM executed successfully"),
        Err(e) => println!("Factorial VM error: {}", e),
    }
    
    let bc2 = create_fibonacci_bytecode();
    println!("\nFibonacci bytecode: {}", hex::encode(&bc2));
    let mut vm2 = VMContext::new(bc2);
    match vm2.execute() {
        Ok(_) => println!("Fibonacci VM executed successfully"),
        Err(e) => println!("Fibonacci VM error: {}", e),
    }
    
    let json = serialize_bytecode(&bc);
    println!("\nSerialized: {}", json);
}