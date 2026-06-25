# ICD-10 Coding Pipeline PoC Spec

## 1. Suggested Tech Stack

- **API framework:** FastAPI
- **Language/runtime:** Python
- **Validation and contracts:** Pydantic request and response models
- **Vector search:** Pinecone
- **Reference corpus:** Official ICD-10-CM and ICD-10-PCS code descriptions and metadata
- **Testing:** pytest unit tests for agent behavior, response schemas, and corpus validation

## 2. Overview & Description

Build a proof of concept for a three-agent clinical coding pipeline that converts clinical encounter text into validated ICD-10 coding recommendations.

The pipeline should expose a FastAPI service that accepts a clinical note or encounter summary, coordinates three specialized agents, validates proposed codes against an ICD-10-CM/PCS corpus indexed in Pinecone, and returns structured coding recommendations with rationale and validation status.

The intended agent flow is:

- **Clinical extraction agent:** Identifies diagnoses, procedures, clinical evidence, and coding-relevant context from the submitted encounter text.
- **Code recommendation agent:** Proposes ICD-10-CM diagnosis codes and ICD-10-PCS procedure codes using extracted evidence and vector retrieval from Pinecone.
- **Validation and review agent:** Confirms proposed codes exist in the ICD-10-CM/PCS corpus, checks that descriptions align with the clinical evidence, and flags uncertain or unsupported recommendations.


Create 
4. Agent Workflow — Roles & Responsibilities
Now create 3 more orchestator agent as described below
Agent :
Extractor Agent 


Role & Detailed Task:

Parses raw clinical text — physician notes,
discharge summaries, operative reports.
Extracts key clinical entities: primary and
secondary diagnoses (with acute/chronic
qualifiers and severity), procedures performed
(with laterality and approach), medications
administered, relevant lab findings referenced,
Social Determinants of Health (SDOH)
indicators, and coded condition qualifiers 
affecting code selection. Outputs a structured
JSON with confidence scores and source text
evidence for every extracted entity to ensure
downstream auditability.

Output Produced :
clinical_entities.json —
structured diagnoses,
procedures, SDOH with
confidence scores and source
text citations


Agent :
Coder Agent 
Role & Detailed Task:
Receives clinical_entities.json and queries the
Pinecone vector database pre-loaded with the
complete ICD-10-CM and ICD-10-PCS code
corpus. For each extracted diagnosis and
procedure, retrieves the five most semantically
similar codes, selects the most specific
applicable code following official guidelines
(code to highest specificity, correct principal
diagnosis sequencing), and records a
structured justification linking clinical text
evidence to the code selected. Also applies
Hierarchical Condition Category (HCC) flags
for risk-adjusted payment models used in
Medicare Advantage and value-based
contracts.


icd10_coded_output.json — all
mapped codes with
descriptions, specificity
justifications, HCC flags and
clinical evidence citations

Agent :
Auditor Agent 

Role & Detailed Task:
Acts as a critic reviewing the Coder Agent
output against clinical documentation
standards and coding compliance guidelines.
Checks for: incomplete code chains (chest
pain documented but no cardiac evaluation
code assigned), missing secondary diagnoses
clinically implied by documented treatments,
principal diagnosis sequencing errors,
documentation gaps that would trigger a payer
query or Clinical Documentation Improvement
(CDI) escalation, and codes requiring a more
specific qualifier absent from the
documentation. Assigns a completeness score
(0–100) and a submission readiness flag
(Ready / Needs Review / Hold) per note, with
CDI query text templates for every gap
identified.

Output Produced :
audit_report.json — flags by
severity
(Critical/Warning/Informational),
completeness score, CDI query
templates, submission
readiness flag

## 2a. create another agent to generate to Feed the data for test
create another agent to generate to Feed the data for test

## 3. Problem Statement

Clinical coding is operationally critical and error-prone. Manual coding workflows require coders to interpret dense clinical documentation, map findings to diagnosis and procedure code systems, and verify that selected codes are valid and supported.

For a hackathon proof of concept, the goal is to demonstrate how a small multi-agent pipeline can assist this workflow by:

- Extracting coding-relevant evidence from clinical text.
- Recommending ICD-10-CM and ICD-10-PCS codes.
- Validating recommendations against a trusted code corpus.
- Returning transparent rationale so a human coder can review the result.

The PoC is not intended to replace certified medical coders or final compliance review. It should demonstrate assistive automation with clear evidence, validation, and uncertainty handling.

## 6. Hackathon Scope

The hackathon scope is limited to a focused, testable backend proof of concept.

In scope:

- A FastAPI endpoint that accepts clinical encounter text.
- A three-agent orchestration flow for extraction, recommendation, and validation.
- Pinecone retrieval over ICD-10-CM and ICD-10-PCS reference content.
- Corpus validation that rejects or flags codes not found in the reference set.
- Structured JSON output with recommended codes, descriptions, evidence, confidence, and validation status.
- Unit tests covering key agent functions, schema validation, and invalid-code handling.

Out of scope:

- Production EHR integration.
- Billing submission or claim generation.
- PHI persistence.
- Full compliance automation.
- Complete coverage of every specialty-specific coding rule.

## 7. Expected Output

The PoC should produce a working FastAPI service and test suite that demonstrate the pipeline end to end.

Expected API behavior:

- Accept a request containing clinical encounter text.
- Return ICD-10-CM diagnosis recommendations and ICD-10-PCS procedure recommendations when supported by the note.
- Include the matching official code description for each recommendation.
- Include evidence snippets or extracted findings that justify each recommendation.
- Include validation status showing whether each code was found in the ICD-10-CM/PCS corpus.
- Include confidence or review flags for ambiguous, unsupported, or low-confidence cases.

Example response shape:

```json
{
  "success": true,
  "data": {
    "diagnosis_codes": [
      {
        "code": "I10",
        "description": "Essential (primary) hypertension",
        "evidence": "History of hypertension documented in the encounter note.",
        "confidence": 0.91,
        "validation_status": "valid"
      }
    ],
    "procedure_codes": [],
    "review_flags": []
  },
  "error": null
}
```

## 8. Real-World Business Impact

A validated clinical coding assistant can reduce coder research time, improve consistency, and help surface unsupported or invalid code selections before downstream billing workflows.

Potential business benefits include:

- Faster coding turnaround for routine encounters.
- Lower denial risk from invalid or poorly supported codes.
- Better auditability through evidence-linked recommendations.
- More consistent coding suggestions across teams.
- A foundation for future integration with revenue cycle management workflows.
