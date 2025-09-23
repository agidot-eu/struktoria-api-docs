# Struktoria Web Application

Nowoczesna aplikacja webowa do zarządzania dokumentami i bazą wiedzy z zintegrowanymi funkcjonalnościami AI.

## Przegląd

Aplikacja webowa Struktoria to interfejs użytkownika zbudowany w technologii Blazor Server z biblioteką komponentów MudBlazor. Zapewnia intuicyjny dostęp do wszystkich funkcjonalności systemu przez przeglądarkę internetową.

## Architektura aplikacji

### Główne strony

```
Pages/
├── Documents/
│   ├── DocumentBuckets.razor         # Lista bucket-ów dokumentów
│   └── DocumentExplorer.razor        # Explorer dokumentów
├── Knowledge/
│   ├── KnowledgeBuckets.razor        # Lista bucket-ów wiedzy
│   ├── KnowledgeExplorer.razor       # Explorer bazy wiedzy
│   └── LLM/RagChat.razor             # Chat RAG z bazą wiedzy
└── Ai/LLM/LLMTester.razor            # Tester modeli AI
```

## Funkcjonalności

### 1. Zarządzanie Bucket-ami

**Lokalizacja:** `/documents`, `/knowledge`

Uniwersalny komponent `BucketGrid` zapewnia:
- Wyświetlanie listy bucket-ów z paginacją
- Filtrowanie i sortowanie
- Akcje: wyświetl, edytuj, usuń
- Konfigurowalny wygląd kolumn
- Wsparcie dla ikon i statusów

### 2. Explorer Dokumentów/Wiedzy

**Lokalizacja:** `/documents/{bucketId}`, `/knowledge/{bucketId}`

Jednolity interfejs explorer-a składający się z:

#### Lewy panel - Drzewo hierarchii
- Hierarchiczne wyświetlanie folderów/domen
- Lazy loading dzieci
- Ikony wskazujące typ elementu
- Obsługa expand/collapse

#### Prawy panel - Zawartość
- **Breadcrumb navigation** - ścieżka nawigacji
- **Lista elementów** - tabela z elementami bieżącego poziomu
- **Akcje kontekstowe** - menu dla każdego elementu

### 3. RAG Chat

**Lokalizacja:** `/rag-chat/{knowledgeBucketId}`

Zaawansowany interfejs do konwersacji z AI:

#### Lewy panel - Konfiguracja
- **Informacje o bazie wiedzy** - nazwa, opis, ID
- **Wybór modelu AI** - lista dostępnych modeli LLM
- **Ustawienia modelu** - temperature, max tokens, system prompt
- **Konfiguracja RAG** - max chunks, context size, search weight
- **Upload plików** - załączniki do konwersacji
- **Akcje czatu** - czyszczenie, eksport

#### Prawy panel - Konwersacja
- **Historia czatu** - wiadomości użytkownika i AI
- **Informacje kontekstowe** - źródła wiedzy użyte w odpowiedzi
- **Metryki** - tokens użyte, koszt, czas przetwarzania
- **Pole wejściowe** - textarea z obsługą Ctrl+Enter

**Obsługiwane modele:**
- OpenAI (GPT-4o, GPT-4o Mini, GPT-5 Mini)
- Anthropic (Claude 3.5 Sonnet, Claude 4 Sonnet)
- Google (Gemini Pro, Gemini Flash, Gemma)
- Meta (Llama 3.1)

### 4. LLM Tester

**Lokalizacja:** `/llm-tester`

Narzędzie do testowania modeli AI:
- Wybór modelu z rozszerzonej listy
- Konfiguracja parametrów (temperature, max tokens)
- Upload plików jako załączniki
- Historia konwersacji
- Kopiowanie odpowiedzi
- Eksport czatu do JSON

## Komponenty UI

### BucketGrid\<T>

Uniwersalny komponent do wyświetlania list bucket-ów:

**Parametry konfiguracji:**
- `BucketService` - serwis dostarczający dane
- `ViewActionBaseUrl` - URL bazowy dla akcji wyświetlania
- `ShowActions` - czy pokazywać kolumnę akcji
- `ShowIcon`, `ShowCode`, `ShowDescription` - widoczność kolumn

**Customizacja:**
- `CustomActions` - dodatkowe akcje
- `CustomBadges` - niestandardowe badge-e
- `AdditionalColumns` - dodatkowe kolumny

### ExplorerComponent

Główny komponent explorer-a łączący tree view z listą elementów:

**Parametry:**
- `ExplorerState` - serwis stanu explorer-a
- `BucketId` - identyfikator bucket-a

**Funkcjonalności:**
- Synchronizacja między tree view a listą
- Obsługa zdarzeń nawigacji
- Responsywny layout (3/9 kolumn)

### TreeComponent

Hierarchiczny tree view:
- Lazy loading węzłów
- Ikony typu folder/plik
- Obsługa zaznaczenia
- Event callback dla zmiany selekcji

### ItemsListComponent

Tabela z elementami bieżącego poziomu:
- Paginacja server-side
- Filtrowanie globalne
- Akcje kontekstowe
- Tooltips z opisami

## Nawigacja i routing

### Główne ścieżki

- `/` - Strona główna
- `/documents` - Lista bucket-ów dokumentów
- `/documents/{bucketId}` - Explorer dokumentów
- `/knowledge` - Lista bucket-ów wiedzy
- `/knowledge/{bucketId}` - Explorer bazy wiedzy
- `/rag-chat/{knowledgeBucketId}` - Chat RAG
- `/llm-tester` - Tester modeli AI

### Autoryzacja

Wszystkie strony wymagają autoryzacji (`[Authorize]` attribute).

## Responsywność

Aplikacja wykorzystuje system grid MudBlazor:
- **xs="12"** - pełna szerokość na małych ekranach
- **lg="3/9"** - podział 25%/75% na dużych ekranach
- Automatyczne przełączanie na układ pionowy na urządzeniach mobilnych

## State Management

### Serwisy stanu

- `DocumentExplorerStateService` - stan explorer-a dokumentów
- `KnowledgeExplorerStateService` - stan explorer-a wiedzy
- `HeaderTextService` - zarządzanie tytułami stron

### Wzorce komunikacji

- **Event callbacks** - komunikacja parent-child
- **Dependency injection** - wstrzykiwanie serwisów
- **StateHasChanged()** - odświeżanie UI

## Obsługa plików

### Upload plików
- Maksymalny rozmiar: 20MB
- Obsługiwane formaty: PDF, obrazy, dokumenty tekstowe
- Walidacja typu i rozmiaru
- Progress indicator podczas uploadu
- Konwersja do TemporaryFile przez S3 service

### Wyświetlanie plików
- Ikony według typu pliku
- Formatowanie rozmiaru plików
- Tooltips z informacjami
- Akcje download/view

## Personalizacja

### Komponenty
Większość komponentów obsługuje customizację przez parametry:
```razor
<BucketGrid CustomActions="@customActionsTemplate"
            CustomBadges="@customBadgesTemplate"
            AdditionalColumns="@additionalColumnsTemplate" />
```

### Styling
- Bazuje na MudBlazor theme
- CSS classes dla customizacji
- Responsive design patterns
- Dark/light mode support

## Performance

### Optymalizacje
- Server-side paginacja
- Lazy loading w tree view
- Virtualizacja dla dużych list
- Debouncing dla wyszukiwania
- Minimal re-renders

### Caching
- Cached results w serwisach
- Browser caching dla statycznych zasobów
- Session storage dla stanu UI

## Troubleshooting

### Częste problemy
- **Powolne ładowanie tree** - sprawdź paginację API
- **Błędy uploadu** - sprawdź limity rozmiaru pliku
- **Problemy z autoryzacją** - sprawdź sesję w dev tools
- **Błędy RAG** - sprawdź konfigurację modeli AI

