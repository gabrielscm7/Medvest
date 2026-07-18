"""Testes rápidos para diagnosticar a API Key DeepSeek."""
import json, httpx

KEY = "sk-f4aff372004c414abec9531f96cba28c"
BASE = "https://api.deepseek.com/v1"
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def test(desc, status_ok, **kwargs):
    try:
        r = httpx.post(f"{BASE}/chat/completions", headers=HEADERS, json=kwargs, timeout=30)
        ok = r.status_code in status_ok
        print(f"{'PASS' if ok else 'FAIL'} {desc}")
        if not ok:
            print(f"       Status {r.status_code}: {r.json().get('error',{}).get('message','')[:120]}")
        return ok
    except Exception as e:
        print(f"FAIL  {desc} — {type(e).__name__}: {e}")
        return False

print("=== Testes da API DeepSeek ===")

t1 = test("texto puro (classificar questao)", {200},
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "Responda apenas JSON"},
        {"role": "user", "content": 'Classifique: "Qual a capital do Brasil?"'}
    ],
    max_tokens=200,
    response_format={"type": "json_object"})

t2 = test("texto PDF (detectar estrutura)", {200},
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "Voce e um assistente ENEM"},
        {"role": "user", "content": 'Analise: "01. Questao A\n02. Questao B"'}
    ],
    max_tokens=200,
    response_format={"type": "json_object"})

t3 = test("imagem (OCR/visao)", {200, 400},
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "Assistente"},
        {"role": "user", "content": [
            {"type": "text", "text": "O que tem nesta imagem?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,aGVsbG8="}}
        ]}
    ],
    max_tokens=200)

t4 = test("modelo deepseek-v4-pro + imagem", {200, 400},
    model="deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "Assistente"},
        {"role": "user", "content": [
            {"type": "text", "text": "O que tem nesta imagem?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,aGVsbG8="}}
        ]}
    ],
    max_tokens=200)

print()
if not t1: print(">>> Chave invalida ou modelo nao existe")
if not t2: print(">>> API pode estar com rate limit ou outage")
if t1 and t2 and not t3:
    print(">>> CONFIRMADO: DeepSeek nao aceita imagens. Necessario QWEN_API_KEY para OCR/fotos.")
    print(">>> Fluxo de PDF funciona normalmente (usa apenas texto).")
