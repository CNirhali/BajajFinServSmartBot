## 2025-05-15 - [Safety Pattern for Resource-Intensive Tasks]
**Learning:** For actions like 'Re-index all files' that take significant time or resources, a simple button click can lead to accidental wait times or resource consumption. Implementing a confirmation checkbox ('Safety Pattern') that enables the button provides a deliberate friction point that improves user confidence and prevents accidental triggers.
**Action:** Always implement a confirmation checkbox for destructive or resource-heavy actions in Streamlit apps, and provide a `help` tooltip to explain the reason for the friction.
