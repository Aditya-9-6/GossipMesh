package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/printer"
	"go/token"
	"os"
)

type Summary struct {
	PackageName string   `json:"package"`
	Imports     []string `json:"imports"`
	Declarations []string `json:"declarations"`
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: %s <filename.go>\n", os.Args[0])
		os.Exit(1)
	}
	filename := os.Args[1]

	fset := token.NewFileSet()
	node, err := parser.ParseFile(fset, filename, nil, parser.ParseComments)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing %s: %v\n", filename, err)
		os.Exit(1)
	}

	summary := Summary{
		PackageName: node.Name.Name,
		Imports:     []string{},
		Declarations: []string{},
	}

	for _, imp := range node.Imports {
		if imp.Path != nil {
			summary.Imports = append(summary.Imports, imp.Path.Value)
		}
	}

	for _, decl := range node.Decls {
		switch d := decl.(type) {
		case *ast.GenDecl:
			// Types and interfaces
			if d.Tok == token.TYPE {
				var buf bytes.Buffer
				err := printer.Fprint(&buf, fset, d)
				if err == nil {
					summary.Declarations = append(summary.Declarations, buf.String())
				}
			}
		case *ast.FuncDecl:
			// Exported functions and methods
			if d.Name.IsExported() {
				// We only want the signature, not the body
				dCopy := *d
				dCopy.Body = nil
				var buf bytes.Buffer
				err := printer.Fprint(&buf, fset, &dCopy)
				if err == nil {
					summary.Declarations = append(summary.Declarations, buf.String())
				}
			}
		}
	}

	out, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshalling json: %v\n", err)
		os.Exit(1)
	}
	fmt.Println(string(out))
}
