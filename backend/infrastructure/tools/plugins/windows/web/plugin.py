from bs4 import BeautifulSoup
from ddgs import DDGS
import requests
import webbrowser
from backend.core.schemas import ToolSchemaOut
from backend.application.decorators import tool

@tool(
    name="open_link",
    description="Opening a web link",
    parameters={ 
        "type": "object",
        "properties": {
            "path": {
                "type": "string"
            }
        },
        "required": ["path"]
     }
)
def open_link(path: str) -> ToolSchemaOut:
    """Открытие файла или ссылки
    
    Args: 
        path: путь к файлу или http ссылки 
    """
    try:
        if path.startswith(('http://', 'https://')):
            webbrowser.open(path)
            return ToolSchemaOut(
                status="ok"
            )
    except Exception as e:
        return ToolSchemaOut(
            status='error',
            msg=str(e)
        )
    return ToolSchemaOut(
            status='ok',
        )


@tool(
    name="search",
    description="Searching in the Internet and gets results",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }
)
def duckduckgo_search_with_rich_snippets(query: str, num_results: int = 3) -> ToolSchemaOut:
    """Поиск в интернете
    Args:
        query: запрос
        num_results: количество результатов 
    """
    HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}
    try:
        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=num_results))

            for res in search_results:
                url = res.get("href", "")
                title = res.get("title", "Без заголовка")
                snippet = res.get("body", "")
                summary = snippet

                # Пробуем получить больше информации с страницы
                try:
                    if url:
                        page = requests.get(url, headers=HEADERS, timeout=5)
                        soup = BeautifulSoup(page.text, "html.parser")

                        # Meta description
                        meta_desc = soup.find("meta", attrs={"name": "description"})
                        if meta_desc and meta_desc.get("content"):
                            summary += f" | Описание: {meta_desc['content'][:200]}"

                        # First paragraph
                        first_paragraph = soup.find("p")
                        if first_paragraph:
                            summary += f" | Абзац: {first_paragraph.get_text(strip=True)[:200]}"

                except Exception as e:
                    summary += f" | [Ошибка парсинга: {str(e)[:50]}]"

                results.append({
                    "title": title,
                    "url": url,
                    "summary": summary[:400],  # Ограничиваем длину
                    "snippet": snippet[:200]
                })

        return ToolSchemaOut(
                status='ok',
                msg= f"Найдено {len(results)} результатов",
                data={
                    "results": results
                }
            )
        
    except Exception as e:
        return ToolSchemaOut(
            status='error',
            msg=f"Error {e}"
        )