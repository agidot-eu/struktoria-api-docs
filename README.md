# Struktoria

Inteligentny system zarządzania dokumentami i bazą wiedzy z funkcjonalnościami AI i RAG (Retrieval-Augmented Generation).

## Komponenty

### 🔧 API (Struktoria.ApiProxy)
REST API zapewniające:
- **Autoryzację** - logowanie, wylogowanie, zarządzanie sesjami
- **Dokumenty** - zarządzanie plikami, folderami i bucket-ami
- **Bazę wiedzy** - organizacja wiedzy w domeny i źródła
- **AI/RAG** - chat z modelami AI wykorzystującymi bazę wiedzy

### 🌐 Aplikacja WWW (Struktoria.Client)
Nowoczesny interfejs użytkownika:
- **Explorer** - hierarchiczne przeglądanie dokumentów i wiedzy
- **RAG Chat** - konwersacje z AI wykorzystujące bazę wiedzy
- **LLM Tester** - testowanie różnych modeli AI
- **Zarządzanie bucket-ami** - organizacja zasobów

## Kluczowe funkcjonalności

- 📁 **Hierarchiczne zarządzanie dokumentami** z folderami i bucket-ami
- 🧠 **Baza wiedzy** z domenami i źródłami wiedzy  
- 🤖 **Integracja z modelami AI** (OpenAI, Anthropic, Google, Meta)
- 🔍 **RAG (Retrieval-Augmented Generation)** - AI odpowiadające na podstawie bazy wiedzy
- 📤 **Upload i przetwarzanie plików** (PDF, obrazy, dokumenty)
- 🔐 **Autoryzacja sesyjna** z wieloma tenantami
- 📊 **Responsywny interfejs** z zaawansowanymi komponentami


## Dokumentacja

Szczegółowa dokumentacja API i przewodniki użytkownika dostępne w folderze `/docs`.
