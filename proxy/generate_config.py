import os
import sys
import yaml
import urllib.request

# 订阅链接与控制器密钥含凭据，一律从环境变量读取，不写入仓库。
# 用法示例（PowerShell）：
#   $env:MUSE_SUB1_URL = "https://.../subscribe?token=..."
#   $env:MUSE_SUB2_URL = "https://.../s/..."
#   $env:MUSE_PROXY_SECRET = "自定义密钥"
#   python proxy/generate_config.py proxy/config.yaml
DEFAULT_SUB1 = os.environ.get("MUSE_SUB1_URL", "")
DEFAULT_SUB2 = os.environ.get("MUSE_SUB2_URL", "")
DEFAULT_SECRET = os.environ.get("MUSE_PROXY_SECRET", "change-me")

def fetch_yaml(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ClashMeta"})
    with urllib.request.urlopen(req, timeout=15) as res:
        return yaml.safe_load(res.read().decode("utf-8", errors="ignore"))

def build_config(sub1_url=None, sub2_url=None, output_path="config.yaml"):
    sub1_url = sub1_url or DEFAULT_SUB1
    sub2_url = sub2_url or DEFAULT_SUB2
    if not sub1_url or not sub2_url:
        raise RuntimeError(
            "请设置环境变量 MUSE_SUB1_URL / MUSE_SUB2_URL 后再运行，"
            "订阅链接含 token，禁止写入仓库。"
        )
    print("Fetching subscriptions...")
    d1 = fetch_yaml(sub1_url)
    d2 = fetch_yaml(sub2_url)

    all_us = []
    us_names = []

    for p in d1.get("proxies", []):
        name = p.get("name", "")
        if any(k in name.lower() for k in ["美", "us", "united states"]):
            clean_name = f"Sub1-{name}"
            p["name"] = clean_name
            all_us.append(p)
            us_names.append(clean_name)

    for p in d2.get("proxies", []):
        name = p.get("name", "")
        if any(k in name.lower() for k in ["美", "us", "united states"]):
            clean_name = f"Sub2-{name}"
            p["name"] = clean_name
            all_us.append(p)
            us_names.append(clean_name)

    if not us_names:
        raise RuntimeError("No US nodes found in subscriptions!")

    listeners = []
    proxy_groups = [
        {
            "name": "US-AUTO",
            "type": "url-test",
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
            "proxies": list(us_names)
        }
    ]

    for idx, name in enumerate(us_names, 1):
        port = 7890 + idx
        group_name = f"US-GROUP-{idx}"
        proxy_groups.append({
            "name": group_name,
            "type": "fallback",
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
            "proxies": [name, "US-AUTO"]
        })
        listeners.append({
            "name": f"mixed-{port}",
            "type": "mixed",
            "port": port,
            "proxy": group_name
        })

    config = {
        "mixed-port": 7890,
        "allow-lan": True,
        "bind-address": "*",
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "external-controller": "0.0.0.0:9090",
        "secret": DEFAULT_SECRET,
        "listeners": listeners,
        "proxies": all_us,
        "proxy-groups": proxy_groups,
        "rules": [
            "MATCH,US-AUTO"
        ]
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)

    ports_list = [f"http://proxy:{7890 + i}" for i in range(1, len(us_names) + 1)]
    print(f"Generated {output_path} with {len(us_names)} US proxy groups on ports 7891 - {7890 + len(us_names)}.")
    return ports_list

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    build_config(output_path=out)
