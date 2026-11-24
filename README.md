# SassyQueenCore

**A personality-driven AI system built around memory, continuity, configurable integrations and real-world interaction.**

SassyQueenCore is an experimental AI companion and research project focused on creating a distinctive, persistent AI personality through software engineering.

Rather than treating personality as a temporary system prompt, the project brings together conversational behaviour, memory architecture, configurable language-model integrations, plugins and optional hardware interfaces.

SassyQueenCore is the technical implementation of an idea: giving a deliberately designed AI personality continuity, character and a recognisable way of interacting with the world.

## Core Features

- **Distinctive AI personality:** A configurable personality designed to be witty, expressive, curious, sarcastic and conversational.
- **Memory architecture:** Persistent memory components intended to support continuity across interactions.
- **AI integrations:** Configurable language-model integration, including local and external provider options.
- **Conversational interface:** Python-based interaction and GUI components.
- **Plugin architecture:** Extendable components for additional functionality.
- **Hardware experimentation:** Optional camera, sensor, LED and servo-control configurations.
- **Research-oriented design:** An evolving platform for experimenting with AI interaction, memory and system integration.

Feature availability depends on the selected configuration, installed dependencies and connected hardware.

## Project Status

SassyQueenCore is an actively developed experimental software project.

The repository contains the application, supporting modules, configuration files, integration components and launch utilities.

Some components are optional, experimental or hardware-dependent. Not every feature is enabled or available in every installation.

The project distinguishes between implemented software functionality, configured integrations and future development objectives.

## Requirements

The primary development environment is Windows.

General requirements:

- Windows 10 or later
- Python 3
- pip
- Git
- Dependencies listed in `requirements.txt`

Additional dependencies may be required for particular AI providers, GPU acceleration, voice functionality or hardware integrations.

A compatible language model and its runtime are required for local inference.

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/YOUR_USERNAME/SassyQueenCore.git
cd SassyQueenCore
```

### 2. Create a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Some optional components may require additional dependencies or system-specific configuration.

### 4. Configure the system

Review the configuration files in the `config` directory.

These files control available system settings, AI integration options, memory behaviour and other configurable components.

Do not publish personal memory databases, API credentials, private identity data or local model files.

### 5. Launch SassyQueenCore

On Windows, run:

```powershell
.\SassyQueenCore.bat
```

The launcher performs startup checks and initializes the application's supporting components before launching the main application.

## AI Integration

SassyQueenCore includes configurable language-model integration components.

Depending on configuration and installed dependencies, the system can work with:

- Local language-model runtimes
- External AI providers
- Custom integration endpoints

External providers require their own credentials and may transmit prompts or other information outside the local machine.

Local inference can reduce reliance on external services, but actual offline operation depends on the selected model, runtime and enabled integrations.

## Memory Architecture

Memory is an important part of the SassyQueenCore design.

The project includes components for:

- Memory storage and retrieval
- Short-term and longer-term memory handling
- Memory associations
- Memory integration with conversational components

Persistent memory availability depends on successful initialization and configuration of the relevant components.

Memory data is stored separately from the public source code and should remain private to the installation owner.

## Plugins and Extensibility

SassyQueenCore uses a modular plugin-oriented structure.

The project includes components for memory-related functionality and optional hardware interaction.

Additional integrations and plugins can be developed as the architecture evolves.

Plugin availability depends on configuration and implementation status.

## Hardware Integration

The project includes experimental hardware configuration and interface components.

Potential hardware extensions include:

- Camera input
- Sensors
- LED indicators
- Servo-based physical expressions

Hardware functionality requires compatible devices, drivers, configuration and supporting software.

The presence of a configuration file does not imply that every hardware feature is connected or operational.

## Privacy and Security

SassyQueenCore is designed to support locally managed AI interaction and personal memory.

However, privacy and security depend on the actual deployment configuration.

Important considerations:

- Keep API keys and credentials outside the public repository.
- Do not publish personal memory databases or logs.
- Protect local configuration and identity data.
- Review external AI provider settings before sending private information.
- Do not assume that memory storage is cryptographically secure without independently verified encryption.

The project is experimental software and should not be treated as a certified security product.

## Development Philosophy

SassyQueenCore explores the intersection of:

- AI personality design
- Persistent memory
- Human-AI interaction
- Local AI systems
- Software and hardware integration

The central idea is that a recognisable AI personality can be deliberately designed and supported through engineering, rather than relying on a generic conversational interface alone.

## Contributing

Ideas, technical feedback and contributions are welcome.

Please describe proposed changes clearly and distinguish implemented functionality from experimental or planned features.

## License

License terms will be specified in the repository.

Until a license is added, all rights are reserved by the copyright holder. Public visibility does not automatically grant permission to reuse, modify or redistribute the source code.

## Disclaimer

SassyQueenCore is an experimental software and research project. It is provided without guarantees of uninterrupted operation, security certification or suitability for any particular purpose.