#!/usr/bin/env bash
set -euo pipefail

cd /opt/lab/litellm
umask 077

printf 'LiteLLM local configuration for VM-Gateway\n'
printf 'Do not paste real secrets into repository files or chat.\n\n'

read -r -p 'Provider prefix and model id [openai/gpt-4.1-mini]: ' MODEL_ID
MODEL_ID=${MODEL_ID:-openai/gpt-4.1-mini}

read -r -s -p 'OPENAI_API_KEY: ' OPENAI_API_KEY
printf '\n'
if [ -z "$OPENAI_API_KEY" ]; then
  printf 'ERROR: OPENAI_API_KEY cannot be empty.\n' >&2
  exit 1
fi

read -r -s -p 'LITELLM_MASTER_KEY [Enter keeps current or generates on first setup]: ' LITELLM_MASTER_KEY
printf '\n'
if [ -z "$LITELLM_MASTER_KEY" ]; then
  LITELLM_MASTER_KEY=$(/opt/lab/litellm/venv/bin/python -c "from dotenv import dotenv_values; print(dotenv_values('/opt/lab/litellm/.env').get('LITELLM_MASTER_KEY', ''))")
  if [ -n "$LITELLM_MASTER_KEY" ]; then
    printf 'Keeping existing LITELLM_MASTER_KEY.\n'
  else
    LITELLM_MASTER_KEY=$(python3 -c "import secrets; print('sk-lab-' + secrets.token_urlsafe(32))")
    printf 'Generated LITELLM_MASTER_KEY (shown once; save it securely): %s\n' "$LITELLM_MASTER_KEY"
  fi
fi

cat > .env <<ENVEOF
OPENAI_API_KEY=$OPENAI_API_KEY
LITELLM_MASTER_KEY=$LITELLM_MASTER_KEY
ENVEOF

cat > config.yaml <<CFGEOF
model_list:
  - model_name: laboratory-model
    litellm_params:
      model: $MODEL_ID
      api_key: os.environ/OPENAI_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY

litellm_settings:
  drop_params: true
CFGEOF

chmod 600 .env config.yaml

printf 'Wrote /opt/lab/litellm/.env and /opt/lab/litellm/config.yaml with mode 600.\n'
printf 'Configured model alias: laboratory-model -> %s\n' "$MODEL_ID"
printf 'Next command: sudo systemctl enable --now litellm.service\n'
