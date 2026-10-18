---
name: subtitle-test-data
description: Subtitle files as ideal test data for semantic search and embedding validation
metadata:
  type: reference
  tags: [testing, embeddings, test-data, semantic-search]
---

## Subtitle Files for Semantic Search Testing

Subtitle files (.srt, .vtt, .sub) make excellent test data for semantic search and embedding systems.

### Why Subtitles Work Well

1. **Natural Language**: Real conversational text with context and flow
2. **Sequential Context**: Lines build on each other, testing context window handling
3. **Varied Domains**: Movies, documentaries, lectures provide diverse vocabulary
4. **Timestamp Metadata**: Built-in temporal structure for testing metadata handling
5. **Manageable Size**: Individual subtitle entries are good chunk sizes (typically 1-3 sentences)
6. **Widely Available**: Easy to obtain for testing without licensing concerns

### Characteristics for Embedding Tests

- **Semantic Relationships**: Related dialogue lines test similarity search accuracy
- **Temporal Coherence**: Tests whether embeddings capture narrative flow
- **Speaker Attribution**: Can test multi-speaker scenarios
- **Domain Shifts**: Scene changes test how embeddings handle topic transitions

### Usage in Vector Inspector

Use subtitle files to validate:
- Content column detection across providers
- Embedding quality with different models (OpenAI, Ollama, HuggingFace)
- Search result relevance and ranking
- Metadata extraction and display
- Performance with realistic document collections
