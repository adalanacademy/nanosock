## What is it
Simply a wrapper of stdin/stdout to input from a socket connection and output to the connection.
`ns` dervives from `nc`; netcat. Ns is basically like socat except it works reliably.

## Use Case
llama is an LLM interface for conversational AI.
```bash
python ns.py "llama infer -m <path/to/model>" --port 12345
```
