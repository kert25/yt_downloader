# Workflow

В этом файле описан Git-воркфлоу проекта. Он разработан для
небольшой команды (1–3 человека) и сочетает простоту с порядком.

---

## 1. Ветки

```
main        — стабильный релизный код
develop     — интеграционная ветка (основная разработка)
feature/*   — новые возможности
fix/*       — исправления багов
```

### main

- В `main` попадает только готовый, протестированный код.
- Каждый коммит в `main` — это релизная версия, отмеченная тегом.
- Прямые коммиты в `main` запрещены — только через слияние из `develop`.

### develop

- Ветка для повседневной работы.
- Содержит последние изменения, которые ещё не вышли в релиз.
- От неё ответвляются `feature/*` и `fix/*` ветки.

### feature/<name>

- Для новой функциональности.
- Ответвляется от `develop`.
- После завершения → Pull Request / merge обратно в `develop`.
- Имя — краткое, на английском, через дефис.
  Пример: `feature/quality-selector`, `feature/download-queue`.

### fix/<name>

- Для исправления багов.
- Ответвляется от `develop` (или от `main`, если баг критичный).
- После завершения → merge в `develop` (и в `main` для hotfix).

---

## 2. Процесс работы

### Новая фича

```bash
git checkout develop
git pull origin develop
git checkout -b feature/my-feature
# работаем, коммитим
git commit -m "Add: краткое описание изменений"
git push origin feature/my-feature
# → создать Pull Request в develop
```

### Исправление бага

```bash
git checkout develop
git checkout -b fix/issue-description
# фиксим, коммитим
git commit -m "Fix: краткое описание проблемы и решения"
git push origin fix/issue-description
# → создать Pull Request в develop
```

### Релиз

```bash
git checkout develop
# убедиться, что всё готово
git checkout main
git merge develop
git tag -a v0.x.x -m "v0.x.x"
git push origin main --tags
# → обновить CHANGELOG.md
```

---

## 3. Коммиты

Формат:

```
<type>: <краткое описание>
```

**Типы:**

| Тип     | Когда использовать                           |
| ------- | -------------------------------------------- |
| `Add`   | Новая функциональность                       |
| `Fix`   | Исправление бага                             |
| `Change`| Изменение существующей логики без новой фичи |
| `Remove`| Удаление кода / файлов                       |
| `Docs`  | Документация (README, CHANGELOG, WORKFLOW)   |
| `Style` | Форматирование, отступы, стиль кода          |

Описание — на русском или английском, до ~70 символов,
без точки в конце.

Примеры:

```
Add: выбор качества видео в интерфейсе
Fix: кнопка остаётся неактивной после скачивания
Docs: add workflow description
Remove: first_concept.md from tracking
```

---

## 4. Версионирование

Проект следует [SemVer](https://semver.org/):

- **MAJOR** — ломающие изменения / большие переработки
- **MINOR** — новые фичи (без ломающих изменений)
- **PATCH** — баг-фиксы и мелкие доработки

Для MVP и ранних стадий: `0.x.y`.
Первый стабильный релиз: `1.0.0`.

Теги: `v0.1.0`, `v1.0.0`, `v2.3.1` и т.д.

---

## 5. Changelog

- Каждый релиз описывается в `CHANGELOG.md`.
- Формат: [Keep a Changelog](https://keepachangelog.com/).
- Разделы: `Added`, `Changed`, `Fixed`, `Removed`.
