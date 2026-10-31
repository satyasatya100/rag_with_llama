"""
Prompt Refinement Engine for Generative AI Models
=================================================
Description:
A systematic framework and engine to refine input prompts to effectively
guide generative AI models in producing high-quality, deterministic, and
desired outputs.

Techniques implemented:
1. RTCE Framework (Role, Task, Context, Expectation)
2. Few-Shot In-Context Learning Injection
3. Chain-of-Thought (CoT) Reasoning Guidance
4. Negative Constraints & Guardrails Enforcement
5. Structured Schema / Delimited Output Anchoring
6. Automated Prompt Completeness Scoring (0 - 100)
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class PromptAnalysis:
    """Stores quantitative evaluation of a prompt's completeness and quality."""
    role_score: int          # 0 to 20
    task_score: int          # 0 to 20
    context_score: int       # 0 to 20
    format_score: int        # 0 to 20
    constraint_score: int    # 0 to 20
    total_score: int         # 0 to 100
    detected_weaknesses: List[str] = field(default_factory=list)
    suggested_improvements: List[str] = field(default_factory=list)


@dataclass
class RefinedPromptResult:
    """Holds original prompt, refined prompt, metadata, and comparative analysis."""
    original_prompt: str
    refined_prompt: str
    target_domain: str
    framework_used: str
    analysis_before: PromptAnalysis
    analysis_after: PromptAnalysis
    sample_naive_output: str
    sample_refined_output: str


class PromptAuditor:
    """Audits input prompts to detect ambiguity, lack of context, and missing constraints."""

    ROLE_KEYWORDS = ["act as", "you are", "role of", "expert", "specialist", "engineer", "advisor", "persona"]
    FORMAT_KEYWORDS = ["format", "json", "markdown", "bullet", "table", "schema", "output as", "xml", "csv"]
    CONSTRAINT_KEYWORDS = ["do not", "never", "avoid", "limit", "must not", "maximum", "minimum", "strict", "only"]
    COT_KEYWORDS = ["step by step", "reasoning", "explain each step", "think through", "breakdown", "rationale"]

    @classmethod
    def audit(cls, prompt: str) -> PromptAnalysis:
        prompt_lower = prompt.lower().strip()
        words = prompt_lower.split()
        word_count = len(words)

        # 1. Role Score (0 to 20)
        has_role = any(kw in prompt_lower for kw in cls.ROLE_KEYWORDS)
        role_score = 20 if has_role else 0

        # 2. Task Score (0 to 20)
        # Check task length, verb presence, specificity
        if word_count < 5:
            task_score = 5
        elif word_count < 15:
            task_score = 12
        else:
            task_score = 20

        # 3. Context Score (0 to 20)
        # Check for context indicators (e.g., target audience, scenario details, background)
        context_indicators = ["for", "given", "scenario", "context", "background", "audience", "targeted at", "dataset", "input:"]
        matches_ctx = sum(1 for ind in context_indicators if ind in prompt_lower)
        if matches_ctx >= 2 or word_count > 30:
            context_score = 20
        elif matches_ctx == 1 or word_count > 15:
            context_score = 10
        else:
            context_score = 5

        # 4. Format Score (0 to 20)
        has_format = any(kw in prompt_lower for kw in cls.FORMAT_KEYWORDS)
        format_score = 20 if has_format else 0

        # 5. Constraint Score (0 to 20)
        has_constraint = any(kw in prompt_lower for kw in cls.CONSTRAINT_KEYWORDS)
        constraint_score = 20 if has_constraint else 0

        total_score = role_score + task_score + context_score + format_score + constraint_score

        # Identify weaknesses
        weaknesses = []
        improvements = []

        if not has_role:
            weaknesses.append("Missing explicit Persona/Role specification.")
            improvements.append("Assign a domain expert role (e.g., 'Act as a Senior Data Architect').")

        if task_score < 20:
            weaknesses.append("Task objective is overly vague or brief.")
            improvements.append("Provide explicit, unambiguous task scope with clear action verbs.")

        if context_score < 20:
            weaknesses.append("Insufficient operational context or target audience definition.")
            improvements.append("Supply background parameters, target users, and environment specifications.")

        if not has_format:
            weaknesses.append("Output formatting is completely unconstrained.")
            improvements.append("Specify exact structural format (e.g., JSON schema, Markdown tables, bulleted hierarchy).")

        if not has_constraint:
            weaknesses.append("No negative constraints or guardrails provided.")
            improvements.append("Add boundaries (e.g., 'Do not hallucinate external libraries', 'Limit response to 200 words').")

        return PromptAnalysis(
            role_score=role_score,
            task_score=task_score,
            context_score=context_score,
            format_score=format_score,
            constraint_score=constraint_score,
            total_score=total_score,
            detected_weaknesses=weaknesses,
            suggested_improvements=improvements
        )


class PromptRefiner:
    """Transforms raw, under-specified prompts into robust, production-grade instructions."""

    def __init__(self):
        self.auditor = PromptAuditor()

    def refine(
        self,
        raw_prompt: str,
        role: Optional[str] = None,
        context: Optional[str] = None,
        output_format: Optional[str] = None,
        constraints: Optional[List[str]] = None,
        enable_cot: bool = True,
        few_shot_examples: Optional[List[Dict[str, str]]] = None,
        delimiters: str = "###"
    ) -> RefinedPromptResult:
        """
        Refines a raw prompt applying the RTCE (Role, Task, Context, Expectation)
        and Guardrails methodology.
        """
        analysis_before = self.auditor.audit(raw_prompt)

        # Detect domain heuristics if not supplied
        domain = self._detect_domain(raw_prompt)

        # Infer role if not provided
        inferred_role = role or self._infer_role(domain)

        # Infer context if not provided
        inferred_context = context or f"Operating within a production enterprise environment focused on {domain}."

        # Infer format if not provided
        inferred_format = output_format or self._infer_format(domain)

        # Infer constraints if not provided
        inferred_constraints = constraints or self._infer_constraints(domain)

        # Construct structured refined prompt
        sections = []

        # 1. Role & Identity
        sections.append(f"### [ROLE & OBJECTIVE]\nYou are a {inferred_role}. Your primary objective is to execute the assigned task with high precision, rigorous adherence to instructions, and zero ambiguity.")

        # 2. Context & Background
        sections.append(f"### [CONTEXT & BACKGROUND]\n{inferred_context}")

        # 3. Core Task & Instructions
        task_instruction = f"Execute the following task:\n\"{raw_prompt.strip()}\""
        if enable_cot:
            task_instruction += "\n\nApproach this step-by-step:\n1. Deconstruct the requirements.\n2. Formulate the intermediate logic or reasoning.\n3. Validate the solution against all stated constraints.\n4. Produce the final output."
        sections.append(f"### [TASK INSTRUCTIONS]\n{task_instruction}")

        # 4. Few-Shot Examples (if provided)
        if few_shot_examples:
            examples_str = "Study the following reference examples to understand the expected input-output behavior:\n"
            for idx, ex in enumerate(few_shot_examples, 1):
                examples_str += f"\n--- Example {idx} ---\nInput: {ex.get('input', '')}\nOutput: {ex.get('output', '')}\n"
            sections.append(f"### [REFERENCE EXAMPLES]\n{examples_str.strip()}")

        # 5. Constraints & Guardrails
        constraints_str = "Adhere strictly to the following constraints:\n"
        for idx, c in enumerate(inferred_constraints, 1):
            constraints_str += f"- [C{idx}] {c}\n"
        sections.append(f"### [CONSTRAINTS & GUARDRAILS]\n{constraints_str.strip()}")

        # 6. Expected Output Format
        sections.append(f"### [OUTPUT FORMAT & STRUCTURE]\n{inferred_format}\nDo not include conversational filler (e.g., 'Sure, here is your answer'). Begin directly with the requested output format.")

        refined_prompt_text = "\n\n".join(sections)

        # Audit refined prompt
        analysis_after = self.auditor.audit(refined_prompt_text)

        # Generate illustrative model outputs for comparison
        naive_out, refined_out = self._generate_simulated_outputs(raw_prompt, domain, refined_prompt_text)

        return RefinedPromptResult(
            original_prompt=raw_prompt,
            refined_prompt=refined_prompt_text,
            target_domain=domain,
            framework_used="RTCE + Chain-of-Thought + Constraint Guardrails",
            analysis_before=analysis_before,
            analysis_after=analysis_after,
            sample_naive_output=naive_out,
            sample_refined_output=refined_out
        )

    def _detect_domain(self, prompt: str) -> str:
        prompt_l = prompt.lower()
        if any(w in prompt_l for w in ["code", "python", "function", "script", "algorithm", "api", "database", "sql"]):
            return "Software Engineering & Code Generation"
        elif any(w in prompt_l for w in ["extract", "parse", "json", "entities", "summarize", "table", "data"]):
            return "Information Extraction & Data Structuring"
        elif any(w in prompt_l for w in ["calculate", "math", "interest", "finance", "solve", "probability"]):
            return "Mathematical & Logical Reasoning"
        elif any(w in prompt_l for w in ["email", "write", "marketing", "announcement", "memo", "post", "letter"]):
            return "Executive & Professional Communication"
        else:
            return "General Knowledge & Analytical Processing"

    def _infer_role(self, domain: str) -> str:
        roles = {
            "Software Engineering & Code Generation": "Principal Software Architect specializing in clean code, robust exception handling, and optimal time complexity",
            "Information Extraction & Data Structuring": "Senior Data Extraction Specialist with mastery in parsing unstructured documents into strictly validated JSON schemas",
            "Mathematical & Logical Reasoning": "Lead Quantitative Analyst and Mathematician known for step-by-step rigorous verification",
            "Executive & Professional Communication": "Chief Communications Strategist adept at high-impact, professional executive messaging",
            "General Knowledge & Analytical Processing": "Domain Expert and Subject-Matter Specialist dedicated to accurate, fact-checked responses"
        }
        return roles.get(domain, "Senior Domain Specialist")

    def _infer_format(self, domain: str) -> str:
        formats = {
            "Software Engineering & Code Generation": "Deliver output as production-ready Python 3.12+ code enclosed in markdown code fences (```python ... ```). Include docstrings, type annotations, and unit test assertions.",
            "Information Extraction & Data Structuring": "Deliver output strictly as valid, parseable RFC 8259 JSON format. Do not prepend markdown formatting, preamble, or postscript comments.",
            "Mathematical & Logical Reasoning": "Format your response in two explicit sections:\n1. 'Reasoning & Proof Steps' (detailed breakdown)\n2. 'Final Answer' (boxed or bolded exact numeric/symbolic result).",
            "Executive & Professional Communication": "Format with clear Subject Line, Executive Summary, Key Action Items (bulleted with assigned owners and deadlines), and Sign-off."
        }
        return formats.get(domain, "Deliver a well-structured markdown document with clear headings, concise bullet points, and an executive summary.")

    def _infer_constraints(self, domain: str) -> List[str]:
        base_constraints = [
            "Do not fabricate or hallucinate unverified facts or library dependencies.",
            "Maintain an objective, professional, and clear tone throughout."
        ]
        if "Code" in domain:
            return base_constraints + [
                "Only use standard library modules unless third-party packages are explicitly requested.",
                "Ensure all functions have PEP 484 type hints and comprehensive error handling.",
                "Time complexity must not exceed O(n log n); prioritize memory efficiency."
            ]
        elif "Extraction" in domain:
            return base_constraints + [
                "Extract only values explicitly stated in the source text; do not infer missing data.",
                "Ensure all JSON keys match snake_case conventions.",
                "Ensure null fields are represented as null, not empty strings or omitted keys."
            ]
        elif "Reasoning" in domain:
            return base_constraints + [
                "Show all intermediate arithmetic and formula derivations.",
                "Include unit checks at each transition step."
            ]
        else:
            return base_constraints + [
                "Avoid buzzwords, boilerplate cliches, and repetitive filler phrases.",
                "Strictly keep the total length within 250 words."
            ]

    def _generate_simulated_outputs(self, raw_prompt: str, domain: str, refined_prompt: str) -> Tuple[str, str]:
        """Provides simulated model responses demonstrating the impact of prompt refinement."""
        if "Code" in domain or "csv" in raw_prompt.lower() or "python" in raw_prompt.lower():
            naive = (
                "Here is some python code to do that:\n\n"
                "import csv\n"
                "def parse_file(filename):\n"
                "    with open(filename, 'r') as f:\n"
                "        reader = csv.reader(f)\n"
                "        for row in reader:\n"
                "            print(row)\n\n"
                "You can change this however you like!"
            )
            refined = (
                "```python\n"
                "import csv\n"
                "from pathlib import Path\n"
                "from typing import Generator, List, Dict, Any\n\n"
                "def parse_large_csv_stream(\n"
                "    file_path: Path, \n"
                "    delimiter: str = ','\n"
                ") -> Generator[Dict[str, Any], None, None]:\n"
                "    \"\"\"\n"
                "    Streams rows from a large CSV file without loading the entire file into memory.\n"
                "    \n"
                "    Time Complexity: O(N) where N is total rows.\n"
                "    Space Complexity: O(1) streaming generator.\n"
                "    \"\"\"\n"
                "    if not file_path.exists():\n"
                "        raise FileNotFoundError(f'File not found at: {file_path}')\n"
                "        \n"
                "    with file_path.open(mode='r', encoding='utf-8', errors='replace') as stream:\n"
                "        reader = csv.DictReader(stream, delimiter=delimiter)\n"
                "        for line_num, record in enumerate(reader, start=1):\n"
                "            yield record\n"
                "```\n\n"
                "### Unit Test & Verification:\n"
                "```python\n"
                "# Assertion check\n"
                "assert callable(parse_large_csv_stream)\n"
                "```"
            )
        elif "Extraction" in domain or "json" in raw_prompt.lower():
            naive = (
                "Sure! Here is the info:\n"
                "The patient John Doe is 45 years old. Diagnosed with Type 2 Diabetes.\n"
                "Medications: Metformin 500mg twice daily.\n"
                "Follow up in 2 weeks."
            )
            refined = (
                "{\n"
                '  "patient_name": "John Doe",\n'
                '  "age": 45,\n'
                '  "primary_diagnosis": "Type 2 Diabetes Mellitus",\n'
                '  "prescriptions": [\n'
                "    {\n"
                '      "medication": "Metformin",\n'
                '      "dosage": "500mg",\n'
                '      "frequency": "twice daily"\n'
                "    }\n"
                "  ],\n"
                '  "follow_up_period_days": 14,\n'
                '  "validation_status": "verified"\n'
                "}"
            )
        elif "Reasoning" in domain or "math" in raw_prompt.lower() or "interest" in raw_prompt.lower():
            naive = (
                "The total amount after compound interest is around $14,693. "
                "Because 10,000 * (1 + 0.08)^5 is roughly that number."
            )
            refined = (
                "### 1. Reasoning & Derivation Steps:\n"
                "- Formula: A = P * (1 + r/n)^(n*t)\n"
                "  Where Principal (P) = $10,000.00\n"
                "  Annual rate (r) = 0.08\n"
                "  Compounding frequency (n) = 1 (annually)\n"
                "  Time duration (t) = 5 years\n"
                "- Step 1: Base factor = 1 + 0.08 = 1.08\n"
                "- Step 2: Exponential term = (1.08)^5 = 1.4693280768\n"
                "- Step 3: Compound Value (A) = 10,000 * 1.4693280768 = $14,693.28\n"
                "- Step 4: Net Interest Earned = $14,693.28 - $10,000.00 = $4,693.28\n\n"
                "### 2. Final Answer:\n"
                "**Total Maturity Amount: $14,693.28 | Total Interest Accrued: $4,693.28**"
            )
        else:
            naive = (
                "Subject: Meeting update\n"
                "Hey team, we need to talk about the system outage that happened yesterday. "
                "Please make sure everyone attends the review meeting tomorrow morning."
            )
            refined = (
                "**Subject:** [URGENT] Incident Post-Mortem & Remediation Plan: Database Outage (INC-8921)\n\n"
                "**Executive Summary:**\n"
                "On October 30 at 14:15 UTC, an unexpected failover loop occurred on Primary DB Cluster-A, causing 24 minutes of intermittent API read degradation. Zero data loss occurred.\n\n"
                "**Action Items & Ownership:**\n"
                "- **Root Cause Analysis (RCA) Report:** DevSecOps Team (Owner: Alex M.) | Due: Nov 1, 12:00 UTC\n"
                "- **Connection Pool Scaling Patch:** Backend Platform Team (Owner: Priya S.) | Due: Nov 2, 18:00 UTC\n"
                "- **Post-Incident Review Meeting:** All Technical Leads | Scheduled: Nov 1, 15:00 UTC"
            )
        return naive, refined


def run_benchmark_suite() -> List[RefinedPromptResult]:
    """Runs the prompt refiner over a standardized benchmark suite representing diverse AI tasks."""
    refiner = PromptRefiner()

    test_cases = [
        {
            "prompt": "Write a python script to parse a large csv file.",
            "role": "Principal Systems Engineer specializing in memory-bounded stream processing",
            "context": "Processing 50GB server access logs on a machine with only 4GB RAM without triggering OOM errors.",
            "output_format": "Clean Python 3.12 code using generator expressions with typing and benchmark docstring.",
            "constraints": ["Memory consumption must remain strictly under 256MB", "Handle corrupted UTF-8 rows gracefully"]
        },
        {
            "prompt": "Calculate compound interest on 10000 for 5 years at 8%.",
            "role": "Chartered Financial Analyst (CFA) and Quantitative Auditor",
            "context": "Preparing client wealth management projection with tax adjustments.",
            "output_format": "Explicit step-by-step breakdown followed by a boxed summary of principal, interest, and final value.",
            "constraints": ["Round all dollar values to exactly two decimal places", "Show every mathematical step"]
        },
        {
            "prompt": "Extract patient diagnosis from this note.",
            "role": "Clinical Informatics Specialist and HIPAA Compliance Auditor",
            "context": "Inpatient discharge notes from electronic health record (EHR) systems.",
            "output_format": "Strict RFC 8259 JSON format with schema: patient_name (string), age (int), primary_diagnosis (string), prescriptions (array of objects), follow_up_period_days (int).",
            "constraints": ["Do not assume missing vitals", "Output strictly valid JSON with no conversational text"]
        },
        {
            "prompt": "Write an email about the server crash.",
            "role": "VP of Engineering & Incident Response Commander",
            "context": "Internal post-incident notice to enterprise executive leadership after resolving a 24-minute database failover.",
            "output_format": "Executive memo format: Subject Line, Executive Summary, Root Cause, Action Items with Owners and SLAs.",
            "constraints": ["Strictly under 250 words", "Maintain an accountable, confident, and professional tone"]
        }
    ]

    results = []
    for tc in test_cases:
        res = refiner.refine(
            raw_prompt=tc["prompt"],
            role=tc.get("role"),
            context=tc.get("context"),
            output_format=tc.get("output_format"),
            constraints=tc.get("constraints")
        )
        results.append(res)
    return results


if __name__ == "__main__":
    print("=" * 80)
    print("PROMPT REFINEMENT ENGINE FOR GENERATIVE AI - DEMONSTRATION RUN")
    print("=" * 80)

    results = run_benchmark_suite()
    for idx, r in enumerate(results, 1):
        print(f"\n[Test Case {idx}] Domain: {r.target_domain}")
        print(f"Original Prompt: '{r.original_prompt}'")
        print(f"Before Audit Score: {r.analysis_before.total_score}/100")
        print(f"Detected Weaknesses: {len(r.analysis_before.detected_weaknesses)}")
        print(f"After Audit Score:  {r.analysis_after.total_score}/100")
        print("-" * 50)
        print("REFINED PROMPT SNIPPET:")
        print(r.refined_prompt[:300] + "...\n")
        print("OUTPUT COMPARISON PREVIEW:")
        print(">> Naive Output:")
        print(r.sample_naive_output[:160] + "...")
        print(">> Refined Output:")
        print(r.sample_refined_output[:200] + "...")
        print("=" * 80)
