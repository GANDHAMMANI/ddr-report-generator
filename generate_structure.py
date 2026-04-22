import os

# Define the project structure
structure = {
    "ddr-report-generator": {
        "app": {
            "__init__.py": "",
            "main.py": "",
            "config.py": "",
            "api": {
                "__init__.py": "",
                "routes": {
                    "__init__.py": "",
                    "upload.py": "",
                    "report.py": "",
                    "health.py": "",
                },
            },
            "core": {
                "__init__.py": "",
                "ingestion.py": "",
                "extractor.py": "",
                "merger.py": "",
                "generator.py": "",
                "image_handler.py": "",
            },
            "exporters": {
                "__init__.py": "",
                "docx_exporter.py": "",
                "pdf_exporter.py": "",
                "html_exporter.py": "",
            },
            "models": {
                "__init__.py": "",
                "pipeline.py": "",
                "response.py": "",
            },
            "templates": {
                "ddr_report.html": "",
            },
            "static": {
                "css": {
                    "report.css": "",
                },
                "js": {
                    "upload.js": "",
                },
            },
            "utils": {
                "__init__.py": "",
                "file_handler.py": "",
                "job_store.py": "",
                "logger.py": "",
            },
        },
        "outputs": {
            ".gitkeep": "",
        },
        "uploads": {
            ".gitkeep": "",
        },
        "tests": {
            "__init__.py": "",
            "conftest.py": "",
            "test_ingestion.py": "",
            "test_extractor.py": "",
            "test_merger.py": "",
            "test_generator.py": "",
            "test_api.py": "",
        },
        ".env": "",
        ".env.example": "",
        ".gitignore": "",
        "requirements.txt": "",
        "Dockerfile": "",
        "docker-compose.yml": "",
        "render.yaml": "",
        "README.md": "",
    }
}


def create_structure(base_path, structure):
    for name, content in structure.items():
        path = os.path.join(base_path, name)

        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            # Create file
            with open(path, "w") as f:
                f.write(content)


if __name__ == "__main__":
    create_structure(".", structure)
    print("✅ Project structure created successfully!")