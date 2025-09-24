# Kompletny workflow API - Od dokumentów do RAG

Przewodnik krok po kroku prezentujący pełną ścieżkę od utworzenia bucket-a dokumentów, przez dodanie plików, aż do wygenerowania bazy wiedzy i odpytania modelu RAG.

## Krok 1: Autoryzacja

Przed rozpoczęciem pracy z API należy się zalogować:

<img width="1448" height="406" alt="image" src="https://github.com/user-attachments/assets/c9758202-5f11-456a-ac6f-6bb93791cb6b" />

```http
POST /api/auth/login
Content-Type: application/json

{
  "login": "user@example.com",
  "password": "mypassword",
  "tenantCode": "company123"
}
```

**Odpowiedź:**
<img width="404" height="152" alt="image" src="https://github.com/user-attachments/assets/4d3c305c-a1c1-4bab-853f-8c6a0de424da" />

```json
{
  "message": "Logowanie zakończone sukcesem",
  "isAuthenticated": true,
  "userEmail": "user@example.com",
  "tenantCode": "company123"
}
```


## Krok 2: Utworzenie bucket-a dokumentów

```http
POST /api/documents/buckets/create?name=Company%20Documents&code=comp-docs&description=Main%20company%20document%20storage
```

**Odpowiedź:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Company Documents",
  "code": "comp-docs",
  "description": "Main company document storage",
  "isActive": true,
  "isDefault": false,
  "isPublic": false,
  "createdAt": "2025-01-15T10:30:00Z"
}
```

**Zapisz bucket ID:** `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

## Krok 3: Pobranie węzłów głównych bucket-a

Sprawdź strukturę główną bucket-a:

```http
GET /api/documents/folders/a1b2c3d4-e5f6-7890-abcd-ef1234567890/root-nodes?includeChildrenCount=true
```

**Odpowiedź:**
```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "Root",
    "hasChildren": true,
    "childrenCount": 0,
    "path": "/",
    "type": "Folder"
  }
]
```

## Krok 4: Utworzenie folderu

Utwórz folder w bucket-ie:

```http
POST /api/documents/folders/create
Content-Type: application/json

{
  "bucketId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "parentId": null,
  "name": "Project Alpha",
  "description": "Documents for Project Alpha",
  "sortOrder": 1
}
```

**Odpowiedź:**
```json
{
  "id": "f1e2d3c4-b5a6-9870-fedc-ba0987654321",
  "bucketId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "parentId": null,
  "name": "Project Alpha",
  "description": "Documents for Project Alpha",
  "sortOrder": 1,
  "createdAt": "2025-01-15T10:35:00Z"
}
```

**Zapisz folder ID:** `f1e2d3c4-b5a6-9870-fedc-ba0987654321`

## Krok 5: Upload pliku

Prześlij plik do utworzonego folderu:



**Odpowiedź:**
```json
{
  "id": "d4c3b2a1-0987-6543-21fe-dcba09876543",
  "name": "project-specification.pdf",
  "originalFileName": "project-specification.pdf",
  "contentType": "application/pdf",
  "sizeBytes": 2048576,
  "folderId": "f1e2d3c4-b5a6-9870-fedc-ba0987654321",
  "description": "Project Alpha specification document",
  "uploadedAt": "2025-01-15T10:40:00Z"
}
```

## Krok 6: Upload dodatkowych plików

Dodaj więcej plików dla lepszej bazy wiedzy:

## Krok 7: Utworzenie knowledge bucket-a (RAG)

Przekształć dokumenty w bazę wiedzy do RAG:

```http
POST /api/documents/buckets/create-knowledge
Content-Type: application/json

{
  "name": "Project Alpha Knowledge",
  "code": "proj-alpha-kb",
  "description": "Knowledge base for Project Alpha documents",
  "sourceBucketIds": [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  ],
  "processingOptions": {
    "chunkSize": 1000,
    "chunkOverlap": 200,
    "textFilesOnly": false,
    "includeMetadata": true,
    "priority": 3
  }
}
```

**Odpowiedź:**
```json
{
  "knowledgeBucketId": "9876543210-abcd-ef12-3456-789abcdef012",
  "processingTaskId": "task-567890ab-cdef-1234-5678-90abcdef1234",
  "status": "Inicjalizacja procesowania RAG",
  "message": "Knowledge bucket został utworzony i rozpoczęto przetwarzanie dokumentów do RAG"
}
```

**Zapisz knowledge bucket ID:** `9876543210-abcd-ef12-3456-789abcdef012`

## Krok 8: Sprawdzenie statusu przetwarzania RAG

Monitoruj postęp przetwarzania:

```http
GET /api/documents/buckets/rag-status?ProcessingTaskId=task-567890ab-cdef-1234-5678-90abcdef1234
```

**Odpowiedź (w trakcie):**
```json
{
  "taskId": "task-567890ab-cdef-1234-5678-90abcdef1234",
  "status": "W trakcie przetwarzania",
  "progressPercentage": 75,
  "processedDocuments": 150,
  "totalDocuments": 200,
  "errorCount": 1,
  "startedAt": "2025-01-15T10:45:00Z",
  "completedAt": null
}
```

**Odpowiedź (ukończone):**
```json
{
  "taskId": "task-567890ab-cdef-1234-5678-90abcdef1234",
  "status": "Ukończone",
  "progressPercentage": 100,
  "processedDocuments": 200,
  "totalDocuments": 200,
  "errorCount": 0,
  "startedAt": "2025-01-15T10:45:00Z",
  "completedAt": "2025-01-15T11:15:00Z"
}
```

---

## Krok 9: Listowanie bucket-ów wiedzy

Pobierz listę dostępnych bucket-ów wiedzy:

```http
POST /api/knowledge/buckets/list
Content-Type: application/json

{
  "page": 1,
  "pageSize": 10,
  "sortDefinitions": [],
  "filterDefinitions": []
}
```

**Odpowiedź:**
```json
{
  "items": [
    {
      "id": "9876543210-abcd-ef12-3456-789abcdef012",
      "name": "Project Alpha Knowledge",
      "code": "proj-alpha-kb",
      "description": "Knowledge base for Project Alpha documents",
      "isActive": true,
      "documentsCount": 200,
      "lastProcessed": "2025-01-15T11:15:00Z"
    },
    {
      "id": "other-bucket-id-here",
      "name": "Other Knowledge Base",
      "code": "other-kb",
      "description": "Another knowledge base",
      "isActive": true,
      "documentsCount": 150,
      "lastProcessed": "2025-01-14T15:30:00Z"
    }
  ],
  "totalItems": 2
}
```

## Krok 10: Wybór bucket-a i pierwsza konwersacja RAG

### Proste zapytanie RAG:

```http
GET /api/knowledge/rag-chat/9876543210-abcd-ef12-3456-789abcdef012?prompt=What%20are%20the%20main%20requirements%20for%20Project%20Alpha%3F&model=google%2Fgemini-2.5-flash&systemPrompt=You%20are%20a%20helpful%20AI%20assistant
```

### Zaawansowane zapytanie RAG:

```http
POST /api/knowledge/rag-chat
Content-Type: application/json

{
  "bucketId": "9876543210-abcd-ef12-3456-789abcdef012",
  "prompt": "What are the main requirements for Project Alpha? Please provide detailed analysis with sources.",
  "model": "google/gemini-2.5-flash",
  "systemPrompt": "You are a helpful AI assistant specialized in project analysis. Use the knowledge base to provide detailed, accurate answers with proper source attribution.",
  "temperature": 0.7,
  "maxTokens": 8000,
  "maxChunksCount": 50,
  "maxContextSize": 100000,
  "minSearchWeight": 0.6,
  "includeHeaderHierarchy": true,
  "includeSourceInfo": true,
  "sortByRelevance": true
}
```

**Odpowiedź:**
```json
{
  "generatedText": "Based on the Project Alpha documents in the knowledge base, the main requirements are:\n\n1. **Performance Requirements**: The system must handle 10,000 concurrent users with response time under 200ms.\n\n2. **Security Requirements**: Implementation of OAuth 2.0 authentication and end-to-end encryption.\n\n3. **Scalability Requirements**: Auto-scaling capabilities to handle traffic spikes up to 500% of baseline.\n\n4. **Compliance Requirements**: GDPR compliance for European users and SOC 2 Type II certification.\n\nThese requirements are detailed in the project specification document and requirements analysis.",
  "tokensUsed": 456,
  "contextChunksCount": 12,
  "contextSize": 8450,
  "usedSources": [
    "project-specification.pdf - Section 3.1 Performance",
    "requirements.docx - Security Requirements",
    "project-specification.pdf - Section 4.2 Scalability"
  ],
  "processingTimeMs": 2340,
  "usage": {
    "inputTokens": 245,
    "outputTokens": 211,
    "totalTokens": 456,
    "totalCost": 0.000234
  },
  "model": "google/gemini-2.5-flash",
  "timestamp": "2025-01-15T11:30:00Z"
}
```

## Krok 11: Kontynuacja konwersacji

Zadaj pytanie uzupełniające:

```http
POST /api/knowledge/rag-chat
Content-Type: application/json

{
  "bucketId": "9876543210-abcd-ef12-3456-789abcdef012",
  "prompt": "What specific technologies are recommended for implementing the OAuth 2.0 authentication mentioned in the requirements?",
  "model": "google/gemini-2.5-flash",
  "systemPrompt": "You are a helpful AI assistant specialized in project analysis. Use the knowledge base to provide detailed, accurate answers with proper source attribution.",
  "temperature": 0.7,
  "maxTokens": 8000
}
```

## Krok 12: Sprawdzenie statusu autoryzacji

W dowolnym momencie możesz sprawdzić status sesji:

```http
GET /api/auth/status
```

**Odpowiedź:**
```json
{
  "isAuthenticated": true,
  "userEmail": "user@example.com",
  "tenantCode": "company123"
}
```

## Krok 13: Wylogowanie

Na koniec pracy wyloguj się:

```http
POST /api/auth/logout
```

**Odpowiedź:**
```json
{
  "message": "Wylogowanie zakończone sukcesem"
}
```

## Podsumowanie workflow

1. **Autoryzacja** → logowanie do systemu
2. **Bucket dokumentów** → utworzenie kontenera na pliki
3. **Struktura folderów** → organizacja dokumentów
4. **Upload plików** → dodanie treści
5. **Knowledge bucket** → przetworzenie do RAG
6. **Monitoring** → sprawdzenie statusu przetwarzania
7. **Listowanie** → przegląd dostępnych baz wiedzy
8. **RAG Chat** → konwersacje z AI wykorzystujące wiedzę
9. **Cleanup** → wylogowanie

Ten workflow pokazuje pełną funkcjonalność systemu od zarządzania dokumentami po zaawansowane funkcje AI.
