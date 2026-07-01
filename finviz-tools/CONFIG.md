# LLM Configuration

Set these environment variables to point the intake stage at an OpenAI-compatible endpoint:

```bash
export FINVIZ_LLM_BASE_URL="https://your-host/v1"
export FINVIZ_LLM_MODEL="your-model-name"
export FINVIZ_LLM_API_KEY="your-api-key"
```

## Examples

### OpenAI
```bash
export FINVIZ_LLM_BASE_URL="https://api.openai.com/v1"
export FINVIZ_LLM_MODEL="gpt-4.1-mini"
export FINVIZ_LLM_API_KEY="..."
```

### Local OpenAI-compatible server
```bash
export FINVIZ_LLM_BASE_URL="http://localhost:8000/v1"
export FINVIZ_LLM_MODEL="my-model"
```

## Optional

```bash
export FINVIZ_LLM_TIMEOUT=60
```
