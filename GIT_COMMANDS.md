# Шпаргалка по Git

## Настройка (один раз)
```bash
git config --global user.name "Имя"    # задать имя
git config --global user.email "email" # задать email
```

## Начало работы
```bash
git init          # создать репозиторий в папке
git clone <url>   # скачать репозиторий с GitHub
```

## Ежедневная работа
```bash
git status        # показать что изменилось
git add .         # добавить все файлы в очередь
git add file.py   # добавить конкретный файл
git commit -m ""  # сохранить снимок с описанием
git push          # отправить на GitHub
git pull          # скачать изменения с GitHub
```

## История
```bash
git log           # полная история коммитов
git log --oneline # краткая история (ID + сообщение)
git diff          # показать что изменилось в файлах
```

## Откат
```bash
git checkout .          # отменить все несохранённые изменения
git checkout <ID>       # перейти к конкретному коммиту
git reset --hard <ID>   # откатить проект к коммиту (удалит всё после)
git revert <ID>         # отменить коммит не удаляя историю
```

## Ветки
```bash
git branch            # список веток
git branch new-feat   # создать ветку
git checkout new-feat # переключиться на ветку
git merge new-feat    # слить ветку в текущую
```

## Связь с GitHub
```bash
git remote -v                    # показать адрес репозитория
git remote add origin <url>      # подключить GitHub
git remote set-url origin <url>  # изменить адрес
```
