
use std::fs;
use rust_vm::{VMContext, deserialize_bytecode};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 { return Err("Usage: <json_file>".into()); }
    let json = fs::read_to_string(&args[1])?;
    let bytecode = deserialize_bytecode(&json)?;
    println!("[Rust VM] Loaded {} bytes", bytecode.len());
    let mut vm = VMContext::new(bytecode);
    match vm.execute() { Ok(_) => println!("[Rust VM] Executed successfully"), Err(e) => { println!("[Rust VM] Error: {}", e); return Err(e.into()); } }
    Ok(())
}
