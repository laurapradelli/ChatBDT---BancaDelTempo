## ChatBDT Project

Un'applicazione web basata su **Django 5.0** per l'organizzazione interna delle associazioni di volontariato "Banca del Tempo", che gestisce dinamicamente lo scambio delle ore tra i vari soci, con una doppia possibilità di autenticazione: in quanto socio o in quanto tesoriere.

## Struttura del Progetto

Il progetto è organizzato seguendo la struttura standard di Django:

```text
├── base/                   # App principale del progetto
│   ├── migrations/         # Storico delle modifiche al database
│   ├── templates/base/     # File HTML (Frontend)
│   ├── admin.py            # Gestione dei moduli del database
│   ├── apps.py             # Configurazione dell'applicazione
│   ├── forms.py            # Definizione dei forms HTML
│   ├── models.py           # Definizione delle tabelle del database
│   ├── tests.py            # Test automatizzati per il controllo del codice
│   ├── urls.py             # Gestione degli indirizzi
│   └── views.py            # Logica di elaborazione delle richieste
├── bdt/                    # Configurazione principale del progetto (Settings, URLs)
│   ├── __init__.py         # Package per l'importazione dei settings
│   ├── settings.py         # Configurazioni globali del progetto
│   ├── urls.py             # Indice globale (principale)
│   ├── wsgi.py             # Gestione della comunicazione con i server web per la production
│   └── asgi.py             # Gestione dei protocolli asincroni
├── static/                 # File statici (CSS, Immagini)
│   ├── base/code.css       # Foglio di stile principale
│   └── images/             # Risorse grafiche
├── .env.example            # Template per le variabili d'ambiente
├── manage.py               # Utility di gestione Django
├── package.json            # Dipendenze Node.js (se presenti)
└── requirements.txt        # Dipendenze Python
