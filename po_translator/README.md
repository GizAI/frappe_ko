# PO File Translator

A professional translation tool for Frappe/ERPNext applications using Azure OpenAI API.

## Features

- **Environment-based Configuration**: Load settings from `.env` file
- **CLI Override Support**: Override any setting via command line arguments
- **Interactive Mode**: Prompt for missing configuration when needed
- **Contextual Translation**: Provide system prompts and translation context for better accuracy
- **Chunk Processing**: Handle large files efficiently by processing in chunks
- **Resume Support**: Resume interrupted translations from specific line numbers
- **Backup Creation**: Automatically create backups before modifying files
- **Professional Prompts**: Specialized for business software terminology

## Setup

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure your Azure OpenAI settings in `.env`:**
   ```bash
   # Required settings
   AZURE_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com/
   AZURE_API_KEY=your-api-key-here
   AZURE_DEPLOYMENT_NAME=your-deployment-name
   
   # Optional settings (with defaults)
   TARGET_LANGUAGE=Korean
   CHUNK_SIZE=80
   MAX_RETRIES=3
   RETRY_DELAY=2
   ```

3. **Install dependencies:**
   ```bash
   pip install python-dotenv openai
   ```

## Usage

### Basic Translation
```bash
python po_translator.py path/to/file.po
```

### With CLI Overrides
```bash
python po_translator.py file.po --target-language Japanese --chunk-size 50
```

### Interactive Mode (prompts for missing config)
```bash
python po_translator.py file.po --interactive
```

### Resume from Specific Line
```bash
python po_translator.py file.po --start-line 1000
```

### Limit Number of Entries
```bash
python po_translator.py file.po --max-entries 100
```

## Available Files

The following translation files are available in `../occam/locale/`:

- `drive-ko.po` - Drive (file management) application
- `helpdesk-ko.po` - Helpdesk (customer service) application  
- `raven-ko.po` - Raven (communication platform) application
- `frappe-ko.po` - Frappe framework core
- `erpnext-ko.po` - ERPNext application

## Configuration Options

| Setting | Environment Variable | CLI Argument | Default | Description |
|---------|---------------------|--------------|---------|-------------|
| Azure Endpoint | `AZURE_ENDPOINT` | `--azure-endpoint` | Required | Azure OpenAI endpoint URL |
| API Key | `AZURE_API_KEY` | `--api-key` | Required | Azure OpenAI API key |
| API Version | `AZURE_API_VERSION` | - | `2024-12-01-preview` | Azure OpenAI API version |
| Deployment Name | `AZURE_DEPLOYMENT_NAME` | `--deployment-name` | `gpt-4o-mini` | Model deployment name |
| Target Language | `TARGET_LANGUAGE` | `--target-language` | `Korean` | Translation target language |
| Chunk Size | `CHUNK_SIZE` | `--chunk-size` | `100` | Entries per translation batch |
| Max Retries | `MAX_RETRIES` | - | `3` | Retry attempts for failed requests |
| Retry Delay | `RETRY_DELAY` | - | `2` | Seconds between retry attempts |

## Advanced Configuration

### System Prompt
Customize the AI's behavior by setting `SYSTEM_PROMPT` in your `.env` file:

```bash
SYSTEM_PROMPT=You are a professional software translator specializing in translating Frappe/ERPNext applications. You understand business software terminology and maintain consistency across translations.
```

### Translation Context
Provide additional context about your project:

```bash
TRANSLATION_CONTEXT=This is a translation for Frappe-based applications including Drive (file management), Helpdesk (customer service), and Raven (communication platform). Maintain professional business terminology and user interface consistency.
```

## Examples

### Translate Drive Application
```bash
python po_translator.py ../occam/locale/drive-ko.po
```

### Translate with Custom Settings
```bash
python po_translator.py ../occam/locale/helpdesk-ko.po \
  --target-language Japanese \
  --chunk-size 50 \
  --max-entries 200
```

### Resume Interrupted Translation
```bash
python po_translator.py ../occam/locale/raven-ko.po --start-line 500
```

## Tips

- **Smaller chunk sizes** (50-80) provide better translation quality but take longer
- **Larger chunk sizes** (100-150) are faster but may have lower quality
- Use `--max-entries` for testing with a small subset first
- Always check the backup files (`.backup` extension) if you need to revert changes
- The script automatically skips already translated entries (non-empty msgstr)

## Troubleshooting

1. **Configuration errors**: Use `--interactive` mode to provide missing settings
2. **API errors**: Check your Azure OpenAI deployment name and endpoint
3. **Rate limiting**: Increase `RETRY_DELAY` in your `.env` file
4. **Large files**: Use smaller `CHUNK_SIZE` values for better reliability
