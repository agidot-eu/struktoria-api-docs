# Struktoria API Documentation


REST API dla systemu zarządzania dokumentami i bazą wiedzy z funkcjonalnościami AI/RAG.

## Przegląd

Struktoria API zapewnia programistyczny dostęp do wszystkich funkcjonalności systemu:
- Zarządzanie dokumentami i folderami
- Organizacja bazy wiedzy w domeny i źródła
- Konwersacje AI z wykorzystaniem RAG
- Autoryzacja i zarządzanie sesjami
- Upload i przetwarzanie plików

## Base URL

```
https://..../swagger/index.html
```

## Autoryzacja

API wykorzystuje autoryzację sesyjną. Przed wykorzystaniem większości endpointów należy się zalogować:

```http
POST /api/auth/login
Content-Type: application/json

{
  "login": "user@example.com",
  "password": "password",
  "tenantCode": "tenant123"
}
```

Po zalogowaniu sesja jest automatycznie zarządzana przez ciasteczka HTTP.

## Kontrolery

### AuthController
**Endpoint:** `/api/auth`

Zarządzanie autoryzacją użytkowników:
- `POST /login` - Logowanie do systemu
- `POST /logout` - Wylogowanie i czyszczenie sesji
- `GET /status` - Sprawdzenie statusu autoryzacji

[Szczegółowa dokumentacja](endpoints/auth-controller.md)

### DocumentsController
**Endpoint:** `/api/documents`

Operacje na dokumentach i folderach:

**Bucket Operations:**
- `POST /buckets/create` - Tworzenie nowego bucket-a
- `POST /buckets/list` - Lista bucket-ów z paginacją

**Folder Operations:**
- `GET /folders/{bucketId}/root-nodes` - Węzły główne
- `GET /folders/{parentId}/children` - Dzieci folderu
- `POST /folders/create` - Tworzenie nowego folderu

**File Operations:**
- `POST /files/list` - Lista plików z filtrowaniem
- `GET /files/{documentId}/download-url` - URL do pobrania
- `POST /files/upload` - Upload pliku

**RAG Operations:**
- `POST /buckets/create-knowledge` - Tworzenie knowledge bucket
- `GET /buckets/rag-status` - Status przetwarzania RAG

[Szczegółowa dokumentacja](endpoints/documents-controller.md)

### KnowledgeController
**Endpoint:** `/api/knowledge`

Zarządzanie bazą wiedzy i funkcjonalności RAG:

**Bucket Operations:**
- `POST /buckets/create` - Tworzenie bucket-a wiedzy
- `POST /buckets/list` - Lista bucket-ów wiedzy

**Domain Operations:**
- `GET /domains/{bucketId}/root-nodes` - Główne domeny
- `GET /domains/{parentId}/children` - Poddomeny

**Knowledge Items:**
- `POST /items/list` - Lista elementów wiedzy

**RAG Chat:**
- `GET /rag-chat/{bucketId}` - Proste zapytanie RAG
- `POST /rag-chat` - Zaawansowane zapytanie RAG

**RAG Management:**
- `POST /buckets/{bucketId}/update-rag` - Aktualizacja indeksu RAG
- `GET /rag-update/status/{taskId}` - Status aktualizacji

[Szczegółowa dokumentacja](endpoints/knowledge-controller.md)

### SampleController
**Endpoint:** `/api/sample`

Kontroler testowy wymagający autoryzacji:
- `GET /protected-data` - Testowe dane chronione

[Szczegółowa dokumentacja](endpoints/sample-controller.md)

## Modele danych

### Podstawowe typy
- **IBucket** - Interfejs bucket-a
- **HierarchyNode** - Węzeł hierarchii
- **HierarchyItem** - Element hierarchii
- **TemporaryFile** - Plik tymczasowy

### Modele żądań
- **LoginRequest** - Dane logowania
- **DocumentCreateFolderRequest** - Tworzenie folderu
- **UploadFileRequest** - Upload pliku
- **RagChatRequest** - Zapytanie RAG

### Modele odpowiedzi
- **GridData<T>** - Dane z paginacją
- **RagChatResponse** - Odpowiedź RAG
- **CreateKnowledgeBucketResponse** - Utworzony knowledge bucket

[Pełna dokumentacja modeli](models/)

## Obsługa błędów

API zwraca standardowe kody HTTP:

- **200 OK** - Sukces
- **400 Bad Request** - Błędne dane wejściowe
- **401 Unauthorized** - Brak autoryzacji
- **404 Not Found** - Zasób nie znaleziony
- **500 Internal Server Error** - Błąd serwera

Przykład odpowiedzi błędu:
```json
{
  "message": "Login, hasło i kod tenanta są wymagane"
}
```

[Szczegółowa obsługa błędów](error-handling.md)

## Paginacja

Endpointy zwracające listy używają `SerializableGridState<T>`:

```json
{
  "page": 1,
  "pageSize": 10,
  "sortDefinitions": [],
  "filterDefinitions": []
}
```

Odpowiedź zawiera `GridData<T>`:
```json
{
  "items": [...],
  "totalItems": 100
}
```

## Przykłady użycia

### Podstawowy workflow

1. **Logowanie:**
```bash
curl -X POST /api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"user@example.com","password":"pass","tenantCode":"tenant"}'
```

2. **Tworzenie bucket-a:**
```bash
curl -X POST /api/documents/buckets/create \
  -H "Content-Type: application/json" \
  -d '{"name":"My Bucket","code":"bucket1","description":"Test bucket"}'
```

3. **Upload pliku:**
```bash
curl -X POST /api/documents/files/upload \
  -F "file=@document.pdf" \
  -F "folderId=guid-here"
```

4. **RAG Chat:**
```bash
curl -X POST /api/knowledge/rag-chat \
  -H "Content-Type: application/json" \
  -d '{"bucketId":"guid","prompt":"What is in my documents?","model":"google/gemini-2.5-flash"}'
```



## Ograniczenia

- **Rozmiar pliku:** Maksymalnie 10MB na plik - możliwość wysyłki dużych plików przez S3
- **Rate limiting:** Sprawdź nagłówki odpowiedzi
- **Session timeout:** Sesje wygasają po okresie nieaktywności
- **Modele AI:** Dostępne modele zależą od konfiguracji

