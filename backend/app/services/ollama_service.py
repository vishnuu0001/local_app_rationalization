"""
OllamaService — Local LLM (Ollama) integration for:
  1. Null/missing field prediction across CORENT, CAST, and Industry data
  2. Correlation analysis & insights generation
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# GPU offloading: -1 = all layers to GPU (full CUDA mode), 0 = CPU only.
# Override via OLLAMA_NUM_GPU env var (e.g. OLLAMA_NUM_GPU=0 for CPU-only).
# RTX 4070 SUPER (12 GB VRAM) can handle qwen2.5:14b or smaller fully on-GPU.
_raw_num_gpu = os.getenv("OLLAMA_NUM_GPU", "-1")
try:
    OLLAMA_NUM_GPU: int = int(_raw_num_gpu)
except ValueError:
    OLLAMA_NUM_GPU = -1

# Index of the GPU to use (0 = first GPU).  Override via OLLAMA_MAIN_GPU.
_raw_main_gpu = os.getenv("OLLAMA_MAIN_GPU", "0")
try:
    OLLAMA_MAIN_GPU: int = int(_raw_main_gpu)
except ValueError:
    OLLAMA_MAIN_GPU = 0

# Optional hard-coded preferred model override (e.g. OLLAMA_PREFERRED_MODEL=qwen2.5:14b).
# When set, this model is tried first before the ranked list below.
OLLAMA_PREFERRED_MODEL: Optional[str] = os.getenv("OLLAMA_PREFERRED_MODEL") or None

# Ranked model list — optimised for NVIDIA GPU with 12 GB VRAM (e.g. RTX 4070 SUPER).
# Models are ordered best-quality-first within each VRAM tier.
# Best choice for RTX 4070 SUPER: qwen2.5:14b (~8.9 GB Q4_K_M) — top
# reasoning/quality while still leaving ~3 GB headroom on 12 GB VRAM.
PREFERRED_MODELS = [
    # ── Tier 1 — 12 GB VRAM sweet-spot (recommended for RTX 4070 SUPER) ──
    "qwen2.5:14b",           # 14B Q4_K_M ~8.9 GB — best quality for enterprise analysis
    "qwen2.5:14b-instruct",
    "mistral:7b-instruct",   # 7B Q4 ~4.1 GB — fast, strong instruction following
    "mistral:7b",
    "mistral:latest",
    "mistral",
    "llama3.1:8b",           # 8B Q4 ~4.9 GB — strong reasoning, long context
    "llama3.1:latest",
    "llama3:latest",         # 8B — already installed
    "llama3",
    "llama3:8b",
    "gemma2:9b",             # 9B Q4 ~5.5 GB — Google, excellent benchmarks
    "gemma2:latest",
    # ── Tier 2 — smaller/fast fallbacks ──
    "llama3.2:latest",       # 3B — extremely fast
    "llama3.2",
    "exaone3.5:2.4b",        # 2.4B — very fast
    "phi3:mini",
    "phi3",
    "gemma2:2b",
    "gemma2",
    "moondream:latest",      # ~1.8B — ultra fast
    "starling-lm:7b-alpha-q5_K_M",
    "qwen2.5",
    # ── Tier 3 — large models (only if 12B+ fits) ──
    "codellama:13b",         # 13B ~8.4 GB Q4
    "GLM4:latest",
    "llama2:latest",
    "gpt-oss:20b",           # 20B — requires ~12 GB+ VRAM
    "llama3:70b-instruct",
    "llama3:70b",
]

# Column groups per source (used to build context-rich prompts)
CORENT_SCHEMA_CONTEXT = (
    "architecture_type, business_owner, platform_host, server_type, server_ip, server_name, "
    "operating_system, cpu_core, memory, internal_storage, external_storage, storage_type, "
    "db_storage, db_engine, environment, install_type, virtualization_attributes, "
    "compute_server_hardware_architecture, application_stability, virtualization_state, "
    "storage_decomposition, flash_storage_used, cpu_requirement, memory_ram_requirement, "
    "mainframe_dependency, desktop_dependency, app_os_platform_cloud_suitability, "
    "database_cloud_readiness, integration_middleware_cloud_readiness, "
    "application_hardware_dependency, app_cots_vs_non_cots, cloud_suitability, "
    "volume_external_dependencies, app_load_predictability_elasticity, "
    "financially_optimizable_hardware_usage, distributed_architecture_design, "
    "latency_requirements, ubiquitous_access_requirements, no_production_environments, "
    "no_non_production_environments, ha_dr_requirements, rto_requirements, "
    "rpo_requirements, deployment_geography"
)

CAST_SCHEMA_CONTEXT = (
    "app_id, app_name, application_architecture, source_code_availability, "
    "programming_language, component_coupling, cloud_suitability, "
    "volume_external_dependencies, code_design, server_name"
)

INDUSTRY_SCHEMA_CONTEXT = (
    "app_id, app_name, business_owner, architecture_type, platform_host, "
    "application_type, install_type, capabilities"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Module-level model cache — avoids a HTTP round-trip on every batch call.
# The cache is invalidated after _MODEL_CACHE_TTL seconds so new models pulled
# during a long run are picked up without restarting the server.
import time as _time
_model_cache: Optional[str] = None
_model_cache_ts: float = 0.0
_MODEL_CACHE_TTL: float = 30.0   # seconds


def _available_model(timeout: int = 5) -> Optional[str]:
    """Return the first available Ollama model from PREFERRED_MODELS list.

    Respects ``OLLAMA_PREFERRED_MODEL`` env var — when set and the model is
    installed, it is returned immediately without scanning the ranked list.

    Result is cached for ``_MODEL_CACHE_TTL`` seconds to avoid hammering the
    Ollama /api/tags endpoint inside tight batch loops.
    """
    global _model_cache, _model_cache_ts

    now = _time.monotonic()
    if _model_cache is not None and (now - _model_cache_ts) < _MODEL_CACHE_TTL:
        return _model_cache

    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=timeout)
        if resp.status_code != 200:
            return None
        installed = {m.get("name", "") for m in resp.json().get("models", [])}

        # Honour explicit override first
        if OLLAMA_PREFERRED_MODEL and OLLAMA_PREFERRED_MODEL in installed:
            logger.debug("Ollama: using env-specified model '%s'", OLLAMA_PREFERRED_MODEL)
            _model_cache = OLLAMA_PREFERRED_MODEL
            _model_cache_ts = now
            return _model_cache

        for candidate in PREFERRED_MODELS:
            if candidate in installed:
                _model_cache = candidate
                _model_cache_ts = now
                return _model_cache
        # Use first installed if none in preferred list
        if installed:
            _model_cache = next(iter(installed))
            _model_cache_ts = now
            return _model_cache
        return None
    except Exception as exc:
        logger.warning("Ollama not reachable: %s", exc)
        return None


def _generate(
    model: str,
    prompt: str,
    timeout: int = 30,
    force_json: bool = False,
    num_predict: int = 1024,
) -> str:
    """Call Ollama /api/generate and return the full response text.

    Parameters
    ----------
    force_json : bool
        When True, adds ``"format": "json"`` to the Ollama request so the
        inference engine hard-constrains output to valid JSON.  Use for batch
        prediction calls to prevent small-model free-text preamble.
    num_predict : int
        Maximum tokens to generate.  Increase for large batch payloads.

    GPU notes
    ---------
    ``num_gpu`` is set to ``OLLAMA_NUM_GPU`` (default -1 = all layers on GPU).
    This forces Ollama to fully offload the model to the NVIDIA GPU via CUDA.
    Set ``OLLAMA_NUM_GPU=0`` to fall back to CPU-only inference.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_predict": num_predict,
            # ── GPU acceleration (CUDA) ──────────────────────────────────
            # -1 = offload ALL transformer layers to GPU (full CUDA mode).
            # Requires Ollama built with CUDA support and NVIDIA drivers.
            # Controlled by OLLAMA_NUM_GPU env var (override in .env).
            "num_gpu": OLLAMA_NUM_GPU,
            # Select GPU device index (0 = first GPU, e.g. RTX 4070 SUPER).
            # Controlled by OLLAMA_MAIN_GPU env var.
            "main_gpu": OLLAMA_MAIN_GPU,
        },
    }
    if force_json:
        payload["format"] = "json"
    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Robustly extract the first JSON object from an LLM response.
    The model sometimes wraps JSON in markdown code fences.
    """
    text = _clean_llm_json_text(text)

    # Find the largest {...} block (greedy — handles nested JSON correctly)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Try the whole cleaned text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


def _clean_llm_json_text(text: str) -> str:
    """Remove markdown fences and trim whitespace from LLM output."""
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    return text.strip()


def _extract_top_level_json_objects(text: str) -> List[str]:
    """
    Extract top-level JSON object snippets from arbitrary text.

    This is a best-effort fallback when array parsing fails due to
    one malformed object inside the batch payload.
    """
    objects: List[str] = []
    depth = 0
    start_idx: Optional[int] = None
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if depth == 0:
                start_idx = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start_idx is not None:
                    objects.append(text[start_idx:i + 1])
                    start_idx = None

    return objects


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    """
    Robustly parse a JSON array from an LLM response.

    Strategy:
      1) Parse the matched [...] block directly.
      2) Retry after removing trailing commas before ] or }.
      3) Fallback: parse any recoverable top-level objects individually.
    """
    cleaned = _clean_llm_json_text(text)
    arr_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    candidate = arr_match.group() if arr_match else cleaned

    # Primary parse attempt
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass

    # Common repair: trailing commas like {...,}
    repaired = re.sub(r",\s*([\]}])", r"\1", candidate)
    try:
        parsed = json.loads(repaired)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass

    # Best-effort salvage: parse each recoverable object independently
    recovered: List[Dict[str, Any]] = []
    for obj_text in _extract_top_level_json_objects(candidate):
        try:
            obj = json.loads(obj_text)
            if isinstance(obj, dict):
                recovered.append(obj)
        except json.JSONDecodeError:
            continue

    return recovered


def _parse_batch_prediction_payload(raw_text: str, expected_count: int) -> List[Dict[str, Any]]:
    """
    Parse and normalize LLM batch output into:
      [{"idx": <int>, "predictions": {...}}, ...]

    Accepts multiple JSON shapes to reduce brittle parsing failures:
      - array of {idx, predictions}
      - array of plain prediction objects (mapped by order)
      - object wrapper with list under keys like results/items/data
      - object keyed by numeric idx: {"0": {...}, "1": {...}}
      - single object {idx, predictions} or plain predictions (for 1-record batches)
    """
    cleaned = _clean_llm_json_text(raw_text)

    candidates: List[Dict[str, Any]] = _extract_json_array(cleaned)

    # If array extraction fails, try object-based shapes.
    if not candidates:
        obj = _extract_json(cleaned)
        if isinstance(obj, dict) and obj:
            # Wrapper object containing a list.
            for key in ("results", "items", "data", "predictions", "records"):
                val = obj.get(key)
                if isinstance(val, list):
                    candidates = [item for item in val if isinstance(item, dict)]
                    break

            # Numeric-key map form: {"0": {...}, "1": {...}}
            if not candidates:
                numeric_items: List[Dict[str, Any]] = []
                all_numeric = True
                for key, value in obj.items():
                    if not isinstance(value, dict):
                        all_numeric = False
                        break
                    try:
                        idx = int(str(key))
                    except ValueError:
                        all_numeric = False
                        break
                    numeric_items.append({"idx": idx, "predictions": value})
                if all_numeric and numeric_items:
                    candidates = numeric_items

            # Single object form.
            if not candidates and ("idx" in obj or "predictions" in obj):
                candidates = [obj]
            elif not candidates and expected_count == 1:
                candidates = [obj]

    if not candidates:
        return []

    normalized: List[Dict[str, Any]] = []

    # If salvage returned one dict that is itself a numeric-key map,
    # normalize it before order-based handling.
    if len(candidates) == 1 and isinstance(candidates[0], dict):
        root_obj = candidates[0]
        numeric_items: List[Dict[str, Any]] = []
        all_numeric = True
        for key, value in root_obj.items():
            if not isinstance(value, dict):
                all_numeric = False
                break
            try:
                idx = int(str(key))
            except ValueError:
                all_numeric = False
                break
            numeric_items.append({"idx": idx, "predictions": value})
        if all_numeric and numeric_items:
            return numeric_items

    # Case 1: items already include numeric idx.
    has_explicit_idx = all(isinstance(item.get("idx"), int) for item in candidates)
    if has_explicit_idx:
        for item in candidates:
            idx = item.get("idx")
            if not isinstance(idx, int):
                continue
            preds = item.get("predictions")
            if not isinstance(preds, dict):
                preds = {
                    k: v for k, v in item.items()
                    if k not in ("idx", "known", "null_fields")
                }
            normalized.append({"idx": idx, "predictions": preds})
        return normalized

    # Case 2: no idx field, map items by order.
    for i, item in enumerate(candidates):
        if i >= expected_count:
            break
        if not isinstance(item, dict):
            continue
        preds = item.get("predictions")
        if not isinstance(preds, dict):
            preds = {
                k: v for k, v in item.items()
                if k not in ("idx", "known", "null_fields")
            }
        normalized.append({"idx": i, "predictions": preds})

    return normalized


# ---------------------------------------------------------------------------
# Rule-based pre-fill — populate obvious fields deterministically BEFORE LLM
# to reduce the number of null fields sent to the GPU, improving throughput.
# ---------------------------------------------------------------------------

def apply_heuristic_fills(record: Dict[str, Any], source: str) -> Dict[str, Any]:
    """
    Populate fields that can be derived from other known fields using
    deterministic rules.  Returns a dict of {field: filled_value} for
    every field that was null and could be filled.

    Safe to call before the LLM batch — zero network latency.
    """
    fills: Dict[str, Any] = {}
    _null = lambda f: not record.get(f) or str(record.get(f, "")).strip() == ""

    if source == "cast":
        arch = (record.get("application_architecture") or "").strip()
        lang = (record.get("programming_language") or "").lower()
        coupling = (record.get("component_coupling") or "").lower()

        # Derive application_architecture from programming_language + coupling
        if _null("application_architecture"):
            if "cobol" in lang or "rpg" in lang or "pl/i" in lang:
                fills["application_architecture"] = "Batch"
            elif coupling == "high":
                fills["application_architecture"] = "Monolithic"
            elif coupling in ("low", "very low"):
                fills["application_architecture"] = "Microservices"
            elif any(x in lang for x in ("java", "spring", "kotlin")):
                fills["application_architecture"] = "SOA"
            elif any(x in lang for x in (".net", "c#", "vb.net")):
                fills["application_architecture"] = "N-Tier"
            elif any(x in lang for x in ("python", "node", "ruby", "go", "rust")):
                fills["application_architecture"] = "Web-Based"

        # Use filled arch for cloud_suitability
        effective_arch = fills.get("application_architecture") or arch
        if _null("cloud_suitability") and effective_arch:
            _arch_l = effective_arch.lower()
            if "microservice" in _arch_l or "web" in _arch_l or "soa" in _arch_l:
                fills["cloud_suitability"] = "High"
            elif "monolith" in _arch_l or "batch" in _arch_l or "mainframe" in _arch_l:
                fills["cloud_suitability"] = "Low"
            elif "n-tier" in _arch_l or "client" in _arch_l:
                fills["cloud_suitability"] = "Medium"

        if _null("source_code_availability") and record.get("repo_name"):
            fills["source_code_availability"] = "Available"

    elif source == "corent":
        arch = (record.get("architecture_type") or "").lower()
        os_  = (record.get("operating_system") or "").lower()
        virt = (record.get("virtualization_state") or "").lower()

        if _null("cloud_suitability"):
            if "microservice" in arch or "web" in arch or "soa" in arch:
                fills["cloud_suitability"] = "High"
            elif "monolith" in arch or "mainframe" in arch:
                fills["cloud_suitability"] = "Low"
            elif "n-tier" in arch or "client" in arch:
                fills["cloud_suitability"] = "Medium"
            elif "linux" in os_ or "ubuntu" in os_ or "rhel" in os_ or "centos" in os_:
                fills["cloud_suitability"] = "High"
            elif "windows" in os_:
                fills["cloud_suitability"] = "Medium"
            elif "virtual" in virt or "vm" in virt:
                fills["cloud_suitability"] = "Medium"

        if _null("virtualization_state") and ("vmware" in os_ or "hyper-v" in os_):
            fills["virtualization_state"] = "Virtualized"
        if _null("virtualization_state") and "physical" in (record.get("server_type") or "").lower():
            fills["virtualization_state"] = "Physical"

        if _null("distributed_architecture_design") and arch:
            fills["distributed_architecture_design"] = (
                "Yes" if any(x in arch for x in ("microservice", "soa", "distributed"))
                else "No"
            )

    elif source == "industry":
        app_type = (record.get("application_type") or "").lower()
        if _null("capabilities"):
            if "erp" in app_type:
                fills["capabilities"] = "Finance, HR, Supply Chain, Procurement"
            elif "crm" in app_type:
                fills["capabilities"] = "Customer Management, Sales, Marketing"
            elif "hr" in app_type:
                fills["capabilities"] = "Human Resources, Payroll, Talent Management"
            elif "finance" in app_type or "accounting" in app_type:
                fills["capabilities"] = "Financial Reporting, Accounts Payable/Receivable, Budgeting"
            elif "itsm" in app_type or "helpdesk" in app_type:
                fills["capabilities"] = "Incident Management, Change Management, Service Desk"

    return fills


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class OllamaService:
    """Wraps all Ollama LLM calls used in the correlation pipeline."""

    # ------------------------------------------------------------------ #
    #  Health / status                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_available() -> bool:
        """Return True if Ollama is reachable and has at least one model."""
        return _available_model() is not None

    @staticmethod
    def health_info() -> Dict[str, Any]:
        """Return a dict with Ollama status details (for API exposure)."""
        try:
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if resp.status_code != 200:
                return {"available": False, "models": [], "selected_model": None}
            models = [m.get("name") for m in resp.json().get("models", [])]
            selected = _available_model()
            return {
                "available": True,
                "base_url": OLLAMA_BASE_URL,
                "models": models,
                "selected_model": selected,
            }
        except Exception as exc:
            return {"available": False, "error": str(exc), "models": [], "selected_model": None}

    # ------------------------------------------------------------------ #
    #  Null / missing value prediction                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def predict_missing_fields(
        record: Dict[str, Any],
        source: str = "generic",
        sample_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Dict[str, Any], List[str], Dict[str, float]]:
        """
        Use the LLM to predict null / missing field values in *record*.

        Parameters
        ----------
        record : dict
            Flat dict of fieldname → value.  None / empty string → "NULL".
        source : str
            One of "corent", "cast", "industry" — used to select schema hint.
        sample_records : list[dict] | None
            Up to 3 representative non-null records for few-shot context.

        Returns
        -------
        predictions : dict
            {field_name: predicted_value} for every field that was null.
        predicted_columns : list[str]
            Names of columns that were AI-filled.
        confidence_map : dict
            {field_name: confidence_score (0.0–1.0)}.
            Ollama doesn't expose per-token probabilities, so we use a fixed
            confidence of 0.75 for all LLM predictions (indicating "inferred,
            not measured").
        """
        model = _available_model()
        if model is None:
            return {}, [], {}

        # Identify null fields
        null_fields = [k for k, v in record.items() if v is None or str(v).strip() == ""]
        if not null_fields:
            return {}, [], {}

        # Build known-fields context
        known_pairs = {k: v for k, v in record.items() if v is not None and str(v).strip() != ""}

        # Schema context hint
        schema_hints = {
            "corent": CORENT_SCHEMA_CONTEXT,
            "cast": CAST_SCHEMA_CONTEXT,
            "industry": INDUSTRY_SCHEMA_CONTEXT,
        }.get(source, "")

        # Build few-shot examples
        few_shot_block = ""
        if sample_records:
            examples = []
            for sr in sample_records[:3]:
                example_json = json.dumps(
                    {k: sr.get(k) for k in null_fields if sr.get(k)}, ensure_ascii=False
                )
                examples.append(f"  Example: {example_json}")
            if examples:
                few_shot_block = (
                    "\nHere are example values from similar records:\n"
                    + "\n".join(examples)
                    + "\n"
                )

        prompt = f"""You are an expert enterprise application portfolio analyst.
You have been given a partially complete application record from an IT rationalization assessment.
Your task is to intelligently predict/fill the missing (NULL) fields based on the known field values
and your knowledge of enterprise application patterns.

Schema context ({source} table columns): {schema_hints}

Known field values:
{json.dumps(known_pairs, indent=2, ensure_ascii=False)}
{few_shot_block}
Fields that are NULL and need prediction:
{json.dumps(null_fields, ensure_ascii=False)}

Instructions:
- Analyze the known fields for patterns (e.g. architecture type → cloud suitability, OS → virtualization state).
- Provide the most likely realistic enterprise values for each NULL field.
- Return ONLY a JSON object with keys matching the NULL field names and predicted string values.
- Do NOT include any explanation — only the JSON object.
- If a field cannot reasonably be predicted, use null in the JSON.

JSON predictions:"""

        try:
            raw_response = _generate(model, prompt, timeout=30)
            predictions = _extract_json(raw_response)

            # Only keep keys that were actually null
            predictions = {k: v for k, v in predictions.items() if k in null_fields and v is not None}
            predicted_columns = list(predictions.keys())
            confidence_map = {col: 0.75 for col in predicted_columns}

            logger.info(
                "OllamaService.predict_missing_fields [model=%s, source=%s]: "
                "predicted %d / %d null fields",
                model, source, len(predicted_columns), len(null_fields),
            )
            return predictions, predicted_columns, confidence_map

        except Exception as exc:
            logger.warning("OllamaService: prediction failed — %s", exc)
            return {}, [], {}

    # ------------------------------------------------------------------ #
    #  LLM Correlation Analysis                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_correlation_analysis(
        consolidated_records: List[Dict[str, Any]],
        statistics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ask the LLM to analyse the consolidated dataset and return insights:
          - Overall portfolio findings
          - Cloud readiness summary
          - Risk observations
          - Top recommendations
          - Per-app brief annotations (first 20 apps max)

        Parameters
        ----------
        consolidated_records : list[dict]
            Full consolidated records (use a sample for very large datasets).
        statistics : dict
            Aggregate statistics from the correlation pipeline.

        Returns
        -------
        dict with keys: summary, cloud_readiness_insight, risk_observations,
                        recommendations, per_app_notes, model_used
        """
        model = _available_model()
        if model is None:
            return {
                "available": False,
                "summary": "Ollama LLM not available on localhost:11434. "
                           "Install Ollama and pull a model (e.g. `ollama pull llama3`).",
                "model_used": None,
            }

        # Summarise to avoid huge prompts (max 30 records for the per-app block)
        sample = consolidated_records[:30]
        sample_json = json.dumps(sample, indent=2, ensure_ascii=False, default=str)

        stats_json = json.dumps(statistics, indent=2, ensure_ascii=False, default=str)

        prompt = f"""You are a senior enterprise application portfolio strategist.
You have been provided with a consolidated data set that merges CORENT (infrastructure),
CAST (code analysis), and Industry Template data for {statistics.get('total_apps', 'N/A')} applications.

== Portfolio Statistics ==
{stats_json}

== Sample Consolidated Records (up to 30) ==
{sample_json}

Provide a comprehensive correlation analysis with the following sections.
Return your answer as a single minified JSON object with exactly these keys:
  "summary"            : 2-3 sentence executive summary of the overall portfolio
  "cloud_readiness"    : observations on cloud-readiness distribution and key blockers
  "risk_observations"  : top 3-5 risk findings (string array)
  "recommendations"    : top 5 actionable recommendations (string array)
  "per_app_notes"      : object mapping app_id → one-line annotation (first 20 apps only)
  "correlation_quality": brief assessment of data quality and match confidence

Return ONLY the JSON object. No markdown, no explanation outside the JSON."""

        try:
            raw_response = _generate(model, prompt, timeout=90)
            analysis = _extract_json(raw_response)

            # Ensure required keys exist
            defaults = {
                "summary": "",
                "cloud_readiness": "",
                "risk_observations": [],
                "recommendations": [],
                "per_app_notes": {},
                "correlation_quality": "",
            }
            for key, default in defaults.items():
                if key not in analysis:
                    analysis[key] = default

            analysis["available"] = True
            analysis["model_used"] = model
            return analysis

        except Exception as exc:
            logger.warning("OllamaService: correlation analysis failed — %s", exc)
            return {
                "available": False,
                "error": str(exc),
                "summary": "LLM analysis failed. Check Ollama logs.",
                "model_used": model,
            }

    # ------------------------------------------------------------------ #
    #  Per-app annotation (lightweight, called per record)                 #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Model selection helper                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_selected_model() -> Optional[str]:
        """Return the model that will be used for predictions (first available)."""
        return _available_model()

    # ------------------------------------------------------------------ #
    #  Batch null/missing value prediction (performance-optimised)         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def predict_missing_fields_batch(
        records: List[Dict[str, Any]],
        source: str = "generic",
        batch_size: int = 20,
    ) -> List[Tuple[Dict[str, Any], List[str], Dict[str, float]]]:
        """
        Batch variant of predict_missing_fields.

        Sends up to *batch_size* records to the LLM in a single API call,
        reducing total round-trips from N to ceil(N / batch_size).

        Returns
        -------
        List of (predictions, predicted_columns, confidence_map) in the same
        order as *records*.  Entries with no null fields return ({}, [], {}).
        """
        model = _available_model()
        if model is None:
            return [({}, [], {}) for _ in records]

        schema_hints = {
            "corent": CORENT_SCHEMA_CONTEXT,
            "cast":   CAST_SCHEMA_CONTEXT,
            "industry": INDUSTRY_SCHEMA_CONTEXT,
        }.get(source, "")

        _skip_keys = frozenset((
            "id", "created_at", "updated_at", "template_id",
            "cast_analysis_id", "_ai_predicted", "_ai_confidence", "_ai_model",
        ))

        all_results: List[Tuple[Dict, List, Dict]] = []

        for batch_start in range(0, len(records), batch_size):
            batch = records[batch_start: batch_start + batch_size]
            batch_results: List[Tuple[Dict, List, Dict]] = [({}, [], {}) for _ in batch]

            # Build per-record summaries for the prompt
            batch_items = []
            idx_null_map: Dict[int, List[str]] = {}   # local_idx → null_fields

            for local_idx, record in enumerate(batch):
                null_fields = [
                    k for k, v in record.items()
                    if k not in _skip_keys
                    and (v is None or str(v).strip() == "")
                ]
                if not null_fields:
                    continue
                known = {
                    k: v for k, v in record.items()
                    if k not in _skip_keys
                    and v is not None and str(v).strip() != ""
                }
                batch_items.append({
                    "idx": local_idx,
                    "known": known,
                    "null_fields": null_fields,
                })
                idx_null_map[local_idx] = null_fields

            if not batch_items:
                all_results.extend(batch_results)
                continue

            # Compact schema hint — up to 20 fields for better coverage
            compact_hint = ", ".join(schema_hints.split(",")[:20]) if schema_hints else ""

            # Source-specific field guidance so the LLM prioritises the right columns
            _field_guidance = {
                "corent": (
                    "Field prediction rules:\n"
                    "- app_name: REQUIRED — derive from app_id text, server_name pattern, "
                    "or business_owner. Strip prefixes like 'APP-', expand abbreviations. "
                    "Never return null for app_name.\n"
                    "- architecture_type: choose ONE of: Monolithic, SOA, Client-Server, "
                    "Web-Based, Microservices, N-Tier, Mainframe. Infer from OS, "
                    "virtualization_state, platform_host.\n"
                    "- cloud_suitability: Low / Medium / High. Infer from architecture_type "
                    "and operating_system.\n"
                ),
                "cast": (
                    "Field prediction rules:\n"
                    "- application_architecture: REQUIRED — choose ONE of: Monolithic, SOA, "
                    "Microservices, Client-Server, Web-Based, N-Tier, Batch, Event-Driven. "
                    "Infer from programming_language (COBOL→Batch/Monolithic, Java/Spring→SOA, "
                    ".NET→N-Tier, Python/Node.js→Microservices) AND component_coupling "
                    "(High coupling→Monolithic, Low coupling→Microservices/SOA).\n"
                    "- app_name: expand app_id abbreviation into a readable application name.\n"
                    "- cloud_suitability: infer from programming_language and component_coupling.\n"
                ),
                "industry": (
                    "Field prediction rules:\n"
                    "- app_name: expand app_id into a readable application name using "
                    "business_owner and application_type as context.\n"
                    "- capabilities: list core business functions inferred from application_type "
                    "and architecture_type.\n"
                ),
            }.get(source, "")

            # Scale timeout with batch size: base 20s + 3s per item, cap at 90s
            _batch_timeout = min(20 + 3 * len(batch_items), 90)
            # num_predict: 60 tokens per item is plenty for short field values
            _batch_num_predict = max(512, min(60 * len(batch_items), 1536))

            prompt = (
                f"Enterprise IT portfolio analyst. Table: {source}.\n"
                + (_field_guidance if _field_guidance else "")
                + "Predict null fields. Output ONLY a compact JSON array, no extra text.\n"
                'Format: [{"idx":0,"predictions":{"field":"value"}}]\n'
                f"Records:\n{json.dumps(batch_items, separators=(',',':'), ensure_ascii=False)}\n"
                "JSON:"
            )

            try:
                raw = _generate(model, prompt, timeout=_batch_timeout, force_json=True, num_predict=_batch_num_predict)
                parsed_items = _parse_batch_prediction_payload(raw, expected_count=len(batch))
                if not parsed_items:
                    raise ValueError("Batch response did not contain a parseable JSON array")

                for item in parsed_items:
                    idx = item.get("idx")
                    if not isinstance(idx, int) or idx >= len(batch):
                        continue
                    null_fields = idx_null_map.get(idx, [])
                    preds = {
                        k: v
                        for k, v in item.get("predictions", {}).items()
                        if k in null_fields and v is not None
                    }
                    predicted_cols = list(preds.keys())
                    confidence = {col: 0.75 for col in predicted_cols}
                    batch_results[idx] = (preds, predicted_cols, confidence)
            except Exception as exc:
                # Batch failed — skip this batch rather than falling back to slow
                # per-record calls which would multiply the timeout by batch size.
                logger.warning(
                    "OllamaService.predict_missing_fields_batch "
                    "[source=%s, batch_start=%d]: skipping — %s",
                    source, batch_start, exc,
                )
                # batch_results already initialised to ({}, [], {}) — leave as-is

            logger.info(
                "OllamaService batch [model=%s, source=%s, batch_start=%d]: %d predictions",
                model, source, batch_start,
                sum(len(r[1]) for r in batch_results),
            )
            all_results.extend(batch_results)

        return all_results

    # ------------------------------------------------------------------ #
    #  Deep Portfolio Correlation Analysis                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_deep_correlation_analysis(
        consolidated_records: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        predictions_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deep LLM analysis of the full portfolio *after* blank-value enrichment.

        Extends generate_correlation_analysis with:
          - 3-phase migration roadmap
          - Technical debt summary across the portfolio
          - Top modernisation priorities ranked by urgency

        Parameters
        ----------
        consolidated_records : list[dict]
            Enriched consolidated records (AI blank-filled).
        statistics : dict
            Aggregate stats (match_percentage, total_apps, etc.).
        predictions_summary : dict
            How many fields were AI-predicted, which model, etc.

        Returns
        -------
        dict with keys: summary, cloud_readiness, risk_observations,
                        recommendations, per_app_notes, correlation_quality,
                        migration_roadmap, technical_debt_summary,
                        modernization_priorities, model_used, available
        """
        model = _available_model()
        if model is None:
            return {
                "available": False,
                "summary": (
                    "LLM not reachable on localhost:11434. "
                    "Start Ollama and pull the model: `ollama pull mistral`"
                ),
                "model_used": None,
            }

        # ── Compute real distributions from ALL consolidated records ──────────
        # Consolidated records use SOURCE-PREFIXED field names:
        #   cloud_suitability  → corent_cloud_suitability, cast_cloud_suitability
        #   architecture       → corent_architecture_type, cast_application_architecture
        #   platform_host      → corent_platform_host, industry_platform_host
        #   programming_language → cast_programming_language
        #   environment        → corent_environment
        #   install_type       → corent_install_type, industry_install_type
        def _top_dist_multi(records: List[Dict], *fields: str, top: int = 8) -> Dict[str, int]:
            """Aggregate values across multiple prefixed field aliases into one distribution."""
            dist: Dict[str, int] = {}
            for r in records:
                for field in fields:
                    v = r.get(field)
                    if v and str(v).strip() not in ("", "None", "null", "N/A", "nan"):
                        key = str(v).strip()
                        dist[key] = dist.get(key, 0) + 1
                        break  # use first non-null value per record to avoid double-counting
            return dict(sorted(dist.items(), key=lambda x: -x[1])[:top])

        def _top_dist(records: List[Dict], field: str, top: int = 8) -> Dict[str, int]:
            """Single-field distribution (used for fields that exist in only one source)."""
            dist: Dict[str, int] = {}
            for r in records:
                v = r.get(field)
                if v and str(v).strip() not in ("", "None", "null", "N/A", "nan"):
                    dist[str(v).strip()] = dist.get(str(v).strip(), 0) + 1
            return dict(sorted(dist.items(), key=lambda x: -x[1])[:top])

        total = len(consolidated_records)

        # Cloud suitability: prefer CAST (code-based) then CORENT (infra-based)
        cloud_dist = _top_dist_multi(
            consolidated_records,
            "cast_cloud_suitability", "corent_cloud_suitability",
        )
        # Architecture: prefer CAST application_architecture then CORENT
        arch_dist = _top_dist_multi(
            consolidated_records,
            "cast_application_architecture", "corent_architecture_type",
            "industry_architecture_type",
        )
        # Platform / host: prefer CORENT then Industry
        plat_dist = _top_dist_multi(
            consolidated_records,
            "corent_platform_host", "industry_platform_host",
            top=6,
        )
        # Programming language (CAST only)
        lang_dist = _top_dist(consolidated_records, "cast_programming_language", top=8)
        # Environment (CORENT only)
        env_dist = _top_dist(consolidated_records, "corent_environment", top=6)
        # Install type: prefer CORENT then Industry
        inst_dist = _top_dist_multi(
            consolidated_records,
            "corent_install_type", "industry_install_type",
            top=6,
        )
        # Additional distributions for richer analysis
        os_dist        = _top_dist(consolidated_records, "corent_operating_system", top=8)
        db_engine_dist = _top_dist(consolidated_records, "corent_db_engine", top=6)
        coupling_dist  = _top_dist(consolidated_records, "cast_component_coupling", top=5)
        code_design_dist = _top_dist(consolidated_records, "cast_code_design", top=5)
        app_type_dist  = _top_dist(consolidated_records, "industry_application_type", top=6)
        ha_dr_dist     = _top_dist(consolidated_records, "corent_ha_dr_requirements", top=5)
        stability_dist = _top_dist(consolidated_records, "corent_application_stability", top=5)
        deploy_geo_dist = _top_dist(consolidated_records, "corent_deployment_geography", top=5)
        mainframe_dist = _top_dist(consolidated_records, "corent_mainframe_dependency", top=4)
        cots_dist      = _top_dist(consolidated_records, "corent_app_cots_vs_non_cots", top=4)
        src_avail_dist = _top_dist(consolidated_records, "cast_source_code_availability", top=4)

        # Cross-source cloud agreement analysis
        cloud_agree = cloud_disagree = cloud_partial = 0
        for r in consolidated_records:
            c = (r.get("cast_cloud_suitability") or "").strip().lower()
            o = (r.get("corent_cloud_suitability") or "").strip().lower()
            if c and o:
                if c == o:
                    cloud_agree += 1
                elif ("high" in c and "high" in o) or ("low" in c and "low" in o):
                    cloud_partial += 1
                else:
                    cloud_disagree += 1

        # AI fill stats
        ai_fill_count = sum(1 for r in consolidated_records if r.get("ai_predicted_columns"))
        ai_field_freq: Dict[str, int] = {}
        for r in consolidated_records:
            for col in (r.get("ai_predicted_columns") or []):
                ai_field_freq[col] = ai_field_freq.get(col, 0) + 1
        top_ai_fields = dict(sorted(ai_field_freq.items(), key=lambda x: -x[1])[:10])

        portfolio_distributions = {
            "total_apps":                     total,
            "match_percentage":               statistics.get("match_percentage"),
            "corent_source_rows":             statistics.get("corent_source_rows", 0),
            "cast_source_rows":               statistics.get("cast_source_rows", 0),
            "industry_source_rows":           statistics.get("industry_source_rows", 0),
            "apps_with_ai_fill":              ai_fill_count,
            "top_ai_predicted_fields":        top_ai_fields,
            # Cloud
            "cloud_suitability_dist":         cloud_dist,
            "corent_cloud_suitability_dist":  _top_dist(consolidated_records, "corent_cloud_suitability"),
            "cast_cloud_suitability_dist":    _top_dist(consolidated_records, "cast_cloud_suitability"),
            "cross_source_cloud_agreement":   {
                "agree": cloud_agree, "partial": cloud_partial, "disagree": cloud_disagree
            },
            # Architecture & code
            "cast_architecture_dist":         _top_dist(consolidated_records, "cast_application_architecture"),
            "corent_architecture_dist":       _top_dist(consolidated_records, "corent_architecture_type"),
            "programming_language_dist":      lang_dist,
            "component_coupling_dist":        coupling_dist,
            "code_design_dist":               code_design_dist,
            "source_code_availability_dist":  src_avail_dist,
            # Infrastructure
            "platform_host_dist":             plat_dist,
            "operating_system_dist":          os_dist,
            "db_engine_dist":                 db_engine_dist,
            "environment_dist":               env_dist,
            "install_type_dist":              inst_dist,
            "deployment_geography_dist":      deploy_geo_dist,
            # Application profile
            "application_type_dist":          app_type_dist,
            "application_stability_dist":     stability_dist,
            "ha_dr_requirements_dist":        ha_dr_dist,
            "mainframe_dependency_dist":      mainframe_dist,
            "cots_vs_non_cots_dist":          cots_dist,
        }

        # Sample records — use actual prefixed field names present in consolidated records
        _KEEP = {
            "app_id", "app_name",
            # CAST
            "cast_application_architecture", "cast_programming_language",
            "cast_cloud_suitability", "cast_component_coupling",
            "cast_code_design", "cast_source_code_availability",
            # CORENT
            "corent_architecture_type", "corent_platform_host",
            "corent_cloud_suitability", "corent_operating_system",
            "corent_environment", "corent_install_type", "corent_db_engine",
            "corent_application_stability", "corent_mainframe_dependency",
            "corent_deployment_geography", "corent_ha_dr_requirements",
            "corent_app_cots_vs_non_cots",
            # Industry
            "industry_application_type", "industry_platform_host",
            "industry_install_type", "industry_business_owner",
            # AI tracking
            "ai_predicted_columns",
        }
        # Use 15 records — enough for patterns without bloating the prompt/tokens
        sample_slim = [{k: v for k, v in r.items() if k in _KEEP and v not in (None, "", "None")}
                       for r in consolidated_records[:15]]
        sample_json = json.dumps(sample_slim, ensure_ascii=False, default=str)
        stats_json  = json.dumps(portfolio_distributions, ensure_ascii=False, default=str)
        pred_json   = json.dumps(predictions_summary, ensure_ascii=False, default=str)

        prompt = (
            "You are a senior enterprise architect performing application portfolio rationalization.\n"
            "The dataset merges three sources:\n"
            "  - CORENT: infrastructure/server data (fields prefixed corent_)\n"
            "  - CAST:   code analysis data (fields prefixed cast_)\n"
            "  - Industry Template: business context data (fields prefixed industry_)\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Base ALL analysis STRICTLY on the actual distributions and sample records below.\n"
            "2. Quote specific counts and percentages from the data (e.g. '47 of 195 apps').\n"
            "3. Highlight cross-source DISAGREEMENTS (e.g. CAST says High cloud-ready but CORENT says Low).\n"
            "4. Identify the most AI-predicted fields and explain what that means for data confidence.\n"
            "5. Every risk and recommendation must cite actual field values from the data.\n"
            "6. Do NOT write generic boilerplate — every sentence must be tied to the data.\n\n"
            f"=== PORTFOLIO DISTRIBUTIONS ===\n{stats_json}\n\n"
            f"=== AI PREDICTION SUMMARY ===\n{pred_json}\n\n"
            f"=== SAMPLE APP RECORDS (first 25) ===\n{sample_json}\n\n"
            "Return a single minified JSON object with EXACTLY these keys (no extras):\n"
            "{\n"
            '  "summary": "3-sentence executive summary citing exact counts, match%, cloud distribution, '
            'and key finding from cross-source comparison",\n'
            '  "cloud_readiness": "detailed paragraph citing BOTH corent_cloud_suitability_dist AND '
            'cast_cloud_suitability_dist counts, cross-source agreement stats, and top cloud blockers '
            'from architecture/coupling data",\n'
            '  "risk_observations": ["≥5 specific risks each citing actual distribution values, '
            'disagreements between CORENT and CAST, AI-filling gaps, or concerning patterns"],\n'
            '  "recommendations": ["≥5 specific actionable recommendations each tied to '
            'a distribution value or pattern, with priority ordering"],\n'
            '  "per_app_notes": {"<ACTUAL_APP_ID>": "one-line insight combining CAST arch + CORENT infra '
            '+ cloud suitability — use real app_id values from the sample records, NOT the literal string app_id"},\n'
            '  "correlation_quality": "assessment citing source row counts, match%, '
            'AI fill rate, and which fields have highest AI-prediction frequency (data gaps)",\n'
            '  "migration_roadmap": [{"phase": 1, "title": "...", "app_count": 0, '
            '"rationale": "tied to actual cloud_suitability and architecture distribution counts"}],\n'
            '  "technical_debt_summary": "paragraph citing programming_language_dist, '
            'cast_architecture_dist, component_coupling_dist, code_design_dist, '
            'and source_code_availability_dist with exact counts",\n'
            '  "modernization_priorities": [{"app_id": "...", "app_name": "...", '
            '"priority": 1, "rationale": "specific reason from actual field values", '
            '"recommended_action": "Retire|Rehost|Replatform|Refactor|Replace"}]\n'
            "}\n"
            "Return ONLY the JSON object. No markdown fences, no explanations outside JSON."
        )

        try:
            # timeout=160: keeps well within the 180s outer ThreadPoolExecutor budget.
            # num_predict=2000: enough for a detailed response; reduces GPU time ~33%.
            raw = _generate(model, prompt, timeout=160, num_predict=2000)
            analysis = _extract_json(raw)

            defaults = {
                "summary": "",
                "cloud_readiness": "",
                "risk_observations": [],
                "recommendations": [],
                "per_app_notes": {},
                "correlation_quality": "",
                "migration_roadmap": [],
                "technical_debt_summary": "",
                "modernization_priorities": [],
            }
            for key, default in defaults.items():
                if key not in analysis:
                    analysis[key] = default

            # ── Post-process: backfill per_app_notes & modernization_priorities
            # for ALL consolidated records not covered by the LLM sample ──────
            analysis = OllamaService._backfill_full_app_lists(
                analysis, consolidated_records
            )

            analysis["available"]   = True
            analysis["model_used"]  = model
            logger.info(
                "OllamaService.generate_deep_correlation_analysis [model=%s]: done", model
            )
            return analysis

        except Exception as exc:
            logger.warning("OllamaService.generate_deep_correlation_analysis failed: %s", exc)
            return {
                "available": False,
                "error": str(exc),
                "summary": "Deep LLM analysis failed. Check Ollama logs.",
                "model_used": model,
            }

    # ------------------------------------------------------------------ #
    #  Backfill all apps not covered by LLM sample                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _backfill_full_app_lists(
        analysis: Dict[str, Any],
        all_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        After the LLM returns analysis (based on a 15-record sample), add
        rule-based per_app_notes and modernization_priorities for every app
        that the LLM did not annotate.  LLM entries are kept as-is.
        """
        def _pick(*fields: str, record: Dict) -> str:
            for f in fields:
                v = record.get(f)
                if v and str(v).strip() not in ("", "None", "null", "N/A", "nan"):
                    return str(v).strip()
            return ""

        def _rule_annotation(r: Dict) -> str:
            app_id   = _pick("app_id",   record=r)
            app_name = _pick("app_name", record=r) or app_id
            arch     = _pick("cast_application_architecture", "corent_architecture_type",
                             "industry_architecture_type", record=r)
            lang     = _pick("cast_programming_language", record=r)
            cloud    = _pick("cast_cloud_suitability", "corent_cloud_suitability", record=r)
            platform = _pick("corent_platform_host", "industry_platform_host", record=r)
            env      = _pick("corent_environment", record=r)
            os_      = _pick("corent_operating_system", record=r)
            src      = _pick("cast_source_code_availability", record=r)
            coupling = _pick("cast_component_coupling", record=r)
            db_eng   = _pick("corent_db_engine", record=r)
            ha_dr    = _pick("corent_ha_dr_requirements", record=r)

            parts = []
            if arch:
                parts.append(f"{arch} architecture")
            if lang:
                parts.append(f"built in {lang}")
            if platform:
                parts.append(f"runs on {platform}")
            if env:
                parts.append(f"{env} environment")
            if os_:
                parts.append(f"{os_} OS")
            if db_eng:
                parts.append(f"{db_eng} DB")
            if ha_dr:
                parts.append(f"{ha_dr} HA/DR")
            if coupling:
                parts.append(f"{coupling} component coupling")

            cloud_part = f"{cloud} cloud suitability" if cloud else ""
            src_part = (
                "no source code available" if src and "not" in src.lower()
                else ("source code available" if src else "")
            )

            base = f"{app_name}: " + (", ".join(parts) if parts else "infrastructure record")
            extras = [x for x in (cloud_part, src_part) if x]
            if extras:
                base += " — " + ", ".join(extras)
            return base

        def _rule_action_score(r: Dict):
            cloud    = _pick("cast_cloud_suitability", "corent_cloud_suitability", record=r).lower()
            src      = _pick("cast_source_code_availability", record=r).lower()
            coupling = _pick("cast_component_coupling", record=r).lower()
            cots     = _pick("corent_app_cots_vs_non_cots", record=r).lower()
            mainframe = _pick("corent_mainframe_dependency", record=r).lower()

            score = 0
            action = "Rehost"
            rationale_parts: List[str] = []

            if "low" in cloud:
                score += 3; action = "Refactor"
                rationale_parts.append("low cloud readiness")
            elif "medium" in cloud or "moderate" in cloud:
                score += 1; action = "Replatform"
                rationale_parts.append("medium cloud readiness")
            elif "high" in cloud:
                action = "Rehost"
                rationale_parts.append("high cloud readiness")

            if "not" in src and "available" in src:
                score += 2; action = "Replace"
                rationale_parts.append("no source code")
            if "high" in coupling or "tight" in coupling:
                score += 1
                rationale_parts.append("high component coupling")
            if "cots" in cots:
                action = "Replace"
                rationale_parts.append("COTS application")
            if "yes" in mainframe or "dependent" in mainframe:
                score += 2
                rationale_parts.append("mainframe dependency")

            rationale = "; ".join(rationale_parts) if rationale_parts else "standard assessment"
            return score, action, rationale

        # per_app_notes backfill
        merged_notes: Dict[str, Any] = dict(analysis.get("per_app_notes") or {})
        for rec in all_records:
            aid = (rec.get("app_id") or "").strip()
            if not aid or aid in merged_notes:
                continue
            merged_notes[aid] = _rule_annotation(rec)
        analysis["per_app_notes"] = merged_notes

        # modernization_priorities backfill
        llm_prio: List[Dict] = list(analysis.get("modernization_priorities") or [])
        covered: set = {str(p.get("app_id", "")).strip().upper() for p in llm_prio}

        extra: List[Dict] = []
        for rec in all_records:
            aid = (rec.get("app_id") or "").strip()
            if not aid or aid.upper() in covered:
                continue
            score, action, rationale = _rule_action_score(rec)
            extra.append({
                "app_id":             aid,
                "app_name":           (rec.get("app_name") or "").strip() or aid,
                "priority":           0,
                "recommended_action": action,
                "rationale":          rationale,
                "_score":             score,
            })

        extra.sort(key=lambda x: -x.pop("_score", 0))
        for idx, p in enumerate(extra, start=len(llm_prio) + 1):
            p["priority"] = idx

        analysis["modernization_priorities"] = llm_prio + extra
        return analysis

    # ------------------------------------------------------------------ #
    #  Per-app annotation (lightweight, called per record)                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def annotate_application(
        app_record: Dict[str, Any],
        model: Optional[str] = None,
    ) -> str:
        """
        Return a single-sentence LLM annotation for one application record.
        Used to populate the `llm_annotation` field in ConsolidatedApp rows.
        """
        model = model or _available_model()
        if model is None:
            return ""

        # Build a concise record summary
        relevant = {
            k: v for k, v in app_record.items()
            if v and k not in ("ai_predicted_columns", "ai_prediction_confidence",
                               "created_at", "updated_at", "llm_annotation")
        }

        prompt = f"""Summarise this enterprise application in ONE concise sentence (max 25 words)
for an executive IT rationalization report.

Record:
{json.dumps(relevant, ensure_ascii=False, default=str)}

One sentence summary:"""

        try:
            response = _generate(model, prompt, timeout=30)
            # Extract first non-empty line
            for line in response.splitlines():
                line = line.strip().strip('"').strip("'")
                if len(line) > 10:
                    return line
            return response.strip()[:200]
        except Exception:
            return ""
