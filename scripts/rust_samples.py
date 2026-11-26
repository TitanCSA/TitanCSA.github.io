"""Build the standalone first checks for the published Rust bindings."""

from hashlib import sha256


def write_rust_samples(rows, output, base):
    for row in rows:
        if row["ecosystem"] != "cargo":
            continue
        check = row["first_check"]
        module = row["name"].replace("-", "_")
        typed = check["call"] == "client.info()"
        sdk_type = "Interceptor" if typed else "Client"
        value = (
            'serde_json::json!({"installed": value.installed, "active": value.active, "trial_state": value.trial_state})'
            if typed else "value"
        )
        filename = f'rust-{row["edition"]}-check.rs'
        source = f'''fn main() -> Result<(), Box<dyn std::error::Error>> {{
    let mut client = {module}::{sdk_type}::new()?;
    let result = match {check["call"]} {{
        Ok(value) => {value},
        Err(error) if error.code == 2 => serde_json::json!({{"windows_error": 2}}),
        Err(error) => return Err(error.into()),
    }};
    println!("{{result}}");
    Ok(())
}}
'''.encode("utf-8")
        (output / filename).write_bytes(source)
        check.update(
            source_url=base + "assets/" + filename,
            source_sha256=sha256(source).hexdigest(),
            create_example_project_command="cargo new titancsa-check --vcs none",
            save_as="main.rs",
            command_from_app_folder="cargo run",
        )
