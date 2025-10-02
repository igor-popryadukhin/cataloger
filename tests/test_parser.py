from catalog_cli.prompting.parser import parse_response


def test_parse_response_deduplicates_and_normalizes():
    sphere = "Строительство"
    response = """
    ```
    Строительство/Фундамент/Бурение
    строиТельство / Фундамент / Бурение
    Фундамент/Бурение/Ограждения
    Строительство/Фундамент/Заливка
    ```
    """
    parsed = parse_response(sphere, response)
    paths = parsed.normalized_paths
    assert paths[0].startswith(sphere)
    assert len(paths) == len({p.lower() for p in paths})
    assert any(path.endswith("Заливка") for path in paths)


def test_parse_response_auto_prefixes_sphere():
    sphere = "Маркетинг"
    response = "SEO/Аудит/Технический аудит\nМаркетинг/Контент/Блог"
    parsed = parse_response(sphere, response)
    assert all(path.startswith("Маркетинг/") for path in parsed.normalized_paths)
    assert parsed.normalized_paths[0].count("/") >= 2
