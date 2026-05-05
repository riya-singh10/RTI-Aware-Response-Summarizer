"""
Module 2: RTI-Aware Semantic Processing
Detects RTI Act sections, classifies sentences, and structures the response.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    RTI_SECTIONS,
    DENIAL_KEYWORDS,
    INFORMATIVE_KEYWORDS,
    PROCEDURAL_KEYWORDS,
    EVASIVE_KEYWORDS
)


class SentenceCategory(Enum):
    INFORMATIVE = "informative"
    DENIAL = "denial"
    PROCEDURAL = "procedural"
    EVASIVE = "evasive"
    NEUTRAL = "neutral"


@dataclass
class ClassifiedSentence:
    text: str
    category: SentenceCategory
    confidence: float
    section_references: List[str] = field(default_factory=list)
    keywords_found: List[str] = field(default_factory=list)


@dataclass
class StructuredRTIResponse:
    original_text: str
    informative_sentences: List[ClassifiedSentence] = field(default_factory=list)
    denial_sentences: List[ClassifiedSentence] = field(default_factory=list)
    procedural_sentences: List[ClassifiedSentence] = field(default_factory=list)
    evasive_sentences: List[ClassifiedSentence] = field(default_factory=list)
    neutral_sentences: List[ClassifiedSentence] = field(default_factory=list)
    section_references: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'original_text': self.original_text,
            'informative': [{'text': s.text, 'confidence': s.confidence} 
                           for s in self.informative_sentences],
            'denied': [{'text': s.text, 'confidence': s.confidence} 
                      for s in self.denial_sentences],
            'procedural': [{'text': s.text, 'confidence': s.confidence} 
                          for s in self.procedural_sentences],
            'evasive': [{'text': s.text, 'confidence': s.confidence} 
                       for s in self.evasive_sentences],
            'neutral': [{'text': s.text, 'confidence': s.confidence} 
                       for s in self.neutral_sentences],
            'section_references': self.section_references,
            'stats': self.get_stats()
        }
    
    def get_stats(self) -> dict:
        total = (len(self.informative_sentences) + len(self.denial_sentences) + 
                len(self.procedural_sentences) + len(self.evasive_sentences) + 
                len(self.neutral_sentences))
        return {
            'total_sentences': total,
            'informative_count': len(self.informative_sentences),
            'denial_count': len(self.denial_sentences),
            'procedural_count': len(self.procedural_sentences),
            'evasive_count': len(self.evasive_sentences),
            'neutral_count': len(self.neutral_sentences),
            'informative_ratio': len(self.informative_sentences) / total if total > 0 else 0,
            'denial_ratio': len(self.denial_sentences) / total if total > 0 else 0,
        }


def detect_rti_sections(text: str) -> Dict[str, List[str]]:
    """
    Detect references to RTI Act sections in text.
    
    Args:
        text: RTI response text
        
    Returns:
        Dictionary mapping section names to list of matched excerpts
    """
    section_references = {}
    
    for section_name, pattern in RTI_SECTIONS.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        excerpts = []
        
        for match in matches:
            # Get surrounding context (50 chars before and after)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            excerpt = text[start:end].strip()
            excerpts.append(excerpt)
        
        if excerpts:
            section_references[section_name] = excerpts
    
    return section_references


def keyword_score(text: str, keywords: List[str]) -> Tuple[float, List[str]]:
    """
    Calculate keyword match score for text.
    
    Args:
        text: Text to analyze
        keywords: List of keywords to search for
        
    Returns:
        Tuple of (score, list of matched keywords)
    """
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in keywords:
        if keyword.lower() in text_lower:
            found_keywords.append(keyword)
    
    score = len(found_keywords) / len(keywords) if keywords else 0
    return score, found_keywords


def classify_sentence(sentence: str) -> ClassifiedSentence:
    """
    Classify a single sentence into RTI response categories.
    
    Uses rule-based keyword matching with confidence scoring.
    
    Args:
        sentence: Single sentence to classify
        
    Returns:
        ClassifiedSentence with category and confidence
    """
    sentence = sentence.strip()
    if not sentence:
        return ClassifiedSentence(
            text=sentence,
            category=SentenceCategory.NEUTRAL,
            confidence=0.0
        )
    
    # Calculate scores for each category
    denial_score, denial_keywords = keyword_score(sentence, DENIAL_KEYWORDS)
    informative_score, informative_keywords = keyword_score(sentence, INFORMATIVE_KEYWORDS)
    procedural_score, procedural_keywords = keyword_score(sentence, PROCEDURAL_KEYWORDS)
    evasive_score, evasive_keywords = keyword_score(sentence, EVASIVE_KEYWORDS)
    
    # Check for section references
    section_refs = detect_rti_sections(sentence)
    section_list = list(section_refs.keys())
    
    # Boost denial score if Section 8 is referenced
    if 'section_8' in section_refs:
        denial_score += 0.3
    
    # Boost procedural score if Section 7 or transfer mentioned
    if 'section_7' in section_refs or re.search(r'transfer|forward', sentence, re.I):
        procedural_score += 0.2
    
    # Determine category based on highest score
    scores = {
        SentenceCategory.DENIAL: (denial_score, denial_keywords),
        SentenceCategory.INFORMATIVE: (informative_score, informative_keywords),
        SentenceCategory.PROCEDURAL: (procedural_score, procedural_keywords),
        SentenceCategory.EVASIVE: (evasive_score, evasive_keywords),
    }
    
    # Find best category
    best_category = SentenceCategory.NEUTRAL
    best_score = 0.0
    best_keywords = []
    
    for category, (score, keywords) in scores.items():
        if score > best_score:
            best_score = score
            best_category = category
            best_keywords = keywords
    
    if best_score < 0.1:
        best_category = SentenceCategory.NEUTRAL
        best_score = 0.5
    
    return ClassifiedSentence(
        text=sentence,
        category=best_category,
        confidence=min(best_score, 1.0),
        section_references=section_list,
        keywords_found=best_keywords
    )


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences for classification.
    
    Args:
        text: Full RTI response text
        
    Returns:
        List of sentences
    """
    # Split on sentence-ending punctuation
    # Handle common abbreviations to avoid false splits
    text = re.sub(r'(Mr|Mrs|Dr|Prof|Sr|Jr|vs|etc|i\.e|e\.g)\.\s', r'\1<DOT> ', text)
    text = re.sub(r'([Ss]ec|[Nn]o)\.\s', r'\1<DOT> ', text)
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Restore dots
    sentences = [s.replace('<DOT>', '.') for s in sentences]
    
    # Filter out empty sentences and very short ones
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    return sentences


def extract_structured_response(text: str) -> StructuredRTIResponse:
    """
    Main function to process RTI text and extract structured response.
    
    Args:
        text: Cleaned RTI response text
        
    Returns:
        StructuredRTIResponse with classified sentences
    """
    # Detect all section references first
    all_section_refs = detect_rti_sections(text)
    
    # Split into sentences
    sentences = split_into_sentences(text)
    
    # Initialize result
    result = StructuredRTIResponse(
        original_text=text,
        section_references=all_section_refs
    )
    
    # Classify each sentence
    for sentence in sentences:
        classified = classify_sentence(sentence)
        
        if classified.category == SentenceCategory.INFORMATIVE:
            result.informative_sentences.append(classified)
        elif classified.category == SentenceCategory.DENIAL:
            result.denial_sentences.append(classified)
        elif classified.category == SentenceCategory.PROCEDURAL:
            result.procedural_sentences.append(classified)
        elif classified.category == SentenceCategory.EVASIVE:
            result.evasive_sentences.append(classified)
        else:
            result.neutral_sentences.append(classified)
    
    return result


def get_response_summary(structured: StructuredRTIResponse) -> str:
    """
    Generate a text summary of the structured response for Gemini input.
    
    Args:
        structured: Structured RTI response
        
    Returns:
        Formatted summary text
    """
    summary_parts = []
    
    # Information provided
    if structured.informative_sentences:
        summary_parts.append("INFORMATION PROVIDED:")
        for s in structured.informative_sentences:
            summary_parts.append(f"  - {s.text}")
    
    # Information denied
    if structured.denial_sentences:
        summary_parts.append("\nINFORMATION DENIED:")
        for s in structured.denial_sentences:
            summary_parts.append(f"  - {s.text}")
    
    # Procedural responses
    if structured.procedural_sentences:
        summary_parts.append("\nPROCEDURAL RESPONSES:")
        for s in structured.procedural_sentences:
            summary_parts.append(f"  - {s.text}")
    
    # Evasive responses
    if structured.evasive_sentences:
        summary_parts.append("\nEVASIVE/UNCLEAR RESPONSES:")
        for s in structured.evasive_sentences:
            summary_parts.append(f"  - {s.text}")
    
    # Section references
    if structured.section_references:
        summary_parts.append("\nRTI ACT SECTIONS REFERENCED:")
        for section, excerpts in structured.section_references.items():
            summary_parts.append(f"  - {section.replace('_', ' ').title()}")
    
    return '\n'.join(summary_parts)
