"""Build the standalone first-check programs for the published Go bindings."""

from hashlib import sha256


def write_go_samples(rows, output, base):
    for row in rows:
        if row["ecosystem"] != "go":
            continue
        check = row["first_check"]
        edition = row["edition"]
        result = "value" if check["call"] == "client.Info()" else "json.RawMessage(value)"
        error_type = "Error" if result == "value" else "NativeError"
        filename = f"go-{edition}-check.go"
        source = f'''package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"

	sdk "{row["name"]}"
)

func check() (any, error) {{
	client, err := sdk.New()
	if err != nil {{
		return nil, err
	}}
	defer client.Close()

	value, err := {check["call"]}
	if err != nil {{
		var native *sdk.{error_type}
		if errors.As(err, &native) && native.Code == 2 {{
			return map[string]uint32{{"windows_error": native.Code}}, nil
		}}
		return nil, err
	}}
	return {result}, nil
}}

func main() {{
	result, err := check()
	if err == nil {{
		err = json.NewEncoder(os.Stdout).Encode(result)
	}}
	if err != nil {{
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}}
}}
'''.encode("utf-8")
        (output / filename).write_bytes(source)
        check.update(
            source_url=base + "assets/" + filename,
            source_sha256=sha256(source).hexdigest(),
            create_example_project_command="go mod init example.com/titancsa-check",
            save_as="main.go",
            command_from_app_folder="go run .",
        )
