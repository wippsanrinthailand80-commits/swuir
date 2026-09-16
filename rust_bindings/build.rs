fn main() {
    cc::Build::new()
        .file("../swuir_il.c")
        .include("../")
        .flag("-std=c99")
        .flag("-Wall")
        .flag("-Wextra")
        .flag("-O2")
        .compile("swuir_il");
    
    println!("cargo:rustc-link-search=native=/usr/lib");
    println!("cargo:rustc-link-lib=swuir_il");
    println!("cargo:rerun-if-changed=../swuir_il.c");
    println!("cargo:rerun-if-changed=../swuir_il.h");
}