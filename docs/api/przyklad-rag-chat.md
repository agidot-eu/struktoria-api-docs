# Przykładowy flow RAG Chat - Zapytanie o należności klientów

Praktyczny przykład odpytania systemu RAG o zadłużenie klientów.

## Krok 1: Logowanie
<img width="1448" height="406" alt="image" src="https://github.com/user-attachments/assets/c9758202-5f11-456a-ac6f-6bb93791cb6b" />

```http
POST /api/auth/login
Content-Type: application/json

{
  "login": "ksiegowa@firma.pl",
  "password": "SecurePass123!",
  "tenantCode": "firma-abc"
}
```

**Odpowiedź:**
```json
{
  "message": "Logowanie zakończone sukcesem",
  "isAuthenticated": true,
  "userEmail": "ksiegowa@firma.pl",
  "tenantCode": "firma-abc"
}
```

## Krok 2: Wyszukanie bucket-ów wiedzy

<img width="1453" height="339" alt="image" src="https://github.com/user-attachments/assets/81818fa9-fb56-4ba0-b1c0-a9bf00f3de58" />

**UWAGA:** Musisz ustawić `pageSize > 0` (domyślnie w swagger jest 0, co powoduje błąd)

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
      "id": "kb-12345678-abcd-ef90-1234-567890abcdef",
      "name": "Księgowość i Finanse",
      "code": "finance-kb",
      "description": "Baza wiedzy zawierająca dokumenty księgowe, faktury i raporty finansowe",
      "isActive": true,
      "isDefault": false,
      "isPublic": false,
      "icon": "account_balance",
      "color": "primary",
      "createdAt": "2025-01-10T08:00:00Z"
    },
    {
      "id": "kb-87654321-fedc-ba09-8765-43210fedcba9",
      "name": "Dokumenty HR",
      "code": "hr-kb", 
      "description": "Baza wiedzy zasobów ludzkich",
      "isActive": true,
      "isDefault": false,
      "isPublic": false,
      "icon": "people",
      "color": "secondary",
      "createdAt": "2025-01-05T10:30:00Z"
    }
  ],
  "totalItems": 2
}
```

<img width="310" height="19" alt="image" src="https://github.com/user-attachments/assets/bd079c4a-0c25-4cc7-9f98-41f39c1f72ac" />


## Krok 3: Wybór pierwszego bucket-a

Wybieramy pierwszy bucket z listy:
id: 33794b7c-005f-419b-ab72-2ec9462b0ea5

## Krok 4: Zapytanie do RAG Chat

<img width="1436" height="556" alt="image" src="https://github.com/user-attachments/assets/4e374de4-3b28-4d78-843d-e3bf79a6d117" />


**Odpowiedź:**
```json
{
  "generatedText": "Na podstawie dostarczonych danych, suma salda klientów wynosi 100,00 zł.",
  ...
}
```

## Krok 5: Zapytanie uzupełniające

Możemy zadać pytanie uzupełniające o szczegóły:

```http
POST /api/knowledge/rag-chat
Content-Type: application/json

{
  "bucketId": "kb-12345678-abcd-ef90-1234-567890abcdef",
  "prompt": "Pokaż mi szczegółowy podział należności według klientów. Który klient jest winien najwięcej?",
  "model": "google/gemini-2.5-flash",
  "systemPrompt": "Jesteś asystentem księgowym. Analizuj dokumenty finansowe i udzielaj precyzyjnych odpowiedzi dotyczących należności i zobowiązań. Zawsze podawaj konkretne kwoty i źródła danych.",
  "temperature": 0.3,
  "maxTokens": 4000
}
```

**Przykładowa odpowiedź:**
```json
{
  "generatedText": "Szczegółowy podział należności według klientów:\n\n1. **Klient ABC Sp. z o.o.** - 45,00 zł (faktura FV/2025/001)\n2. **Firma XYZ Ltd.** - 35,00 zł (faktura FV/2025/003) \n3. **Przedsiębiorstwo DEF** - 20,00 zł (faktura FV/2025/002)\n\n**Łącznie: 100,00 zł**\n\nNajwiększe zadłużenie ma **Klient ABC Sp. z o.o.** z kwotą 45,00 zł. Termin płatności tej faktury minął 15 dni temu.",
  "tokensUsed": 198,
  "contextChunksCount": 12,
  "contextSize": 6780,
  "usedSources": [
    "Raport_Naleznosci_012025.xlsx - Szczegóły klientów",
    "Faktura_FV_2025_001.pdf - Klient ABC Sp. z o.o.",
    "Faktura_FV_2025_002.pdf - Przedsiębiorstwo DEF",
    "Faktura_FV_2025_003.pdf - Firma XYZ Ltd.",
    "Rejestr_Terminow_Platnosci.xlsx - Daty wymagalności"
  ],
  "processingTimeMs": 3200,
  "usage": {
    "inputTokens": 125,
    "outputTokens": 73,
    "totalTokens": 198,
    "totalCost": 0.000099
  },
  "model": "google/gemini-2.5-flash",
  "timestamp": "2025-01-15T14:27:15Z"
}
```

## Analiza odpowiedzi

### Kluczowe elementy odpowiedzi:

1. **generatedText**: Główna odpowiedź AI z konkretną kwotą 100,00 zł
2. **contextChunksCount**: 8 fragmentów wiedzy użytych do odpowiedzi
3. **usedSources**: Konkretne dokumenty źródłowe z bazy wiedzy
4. **tokensUsed**: 156 tokenów wykorzystanych w zapytaniu
5. **totalCost**: Koszt zapytania (0.000078 USD)

### Zalety tego podejścia:

- **Precyzyjne odpowiedzi** dzięki niskiej temperature (0.3)
- **Źródła danych** - widać, skąd pochodzą informacje
- **Kontekst finansowy** - system rozpoznał księgową naturę pytania
- **Konkretne kwoty** - nie ogólniki, ale dokładne dane

## Możliwe rozszerzenia

Możesz zadać kolejne pytania w tej samej sesji:

- "Które faktury są przeterminowane?"
- "Jaka jest średnia wartość faktury?"
- "Którym klientom wysłano upomnienia?"
- "Pokaż mi trending zadłużenia w ostatnich miesiącach"

## Tips dla lepszych wyników

1. **Używaj precyzyjnych pytań** - "należności" zamiast "pieniądze"
2. **Ustaw niską temperature** (0.1-0.3) dla danych liczbowych
3. **Zwiększ minSearchWeight** (0.7-0.9) dla większej precyzji
4. **Systemowy prompt** powinien definiować rolę (księgowy, analityk)
5. **Upewnij się, że baza wiedzy** zawiera odpowiednie dokumenty finansowe
