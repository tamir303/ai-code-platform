import httpx
from src.worker.celery_app import celery_app
from src.config.settings import get_settings

settings = get_settings()


@celery_app.task(bind=True, name="tasks.batch_code_review")
def batch_code_review_task(self, files: list[dict], user_api_key: str):
    results = []
    total = len(files)

    headers = {
        "Authorization": f"Bearer {user_api_key}",
        "Content-Type": "application/json"
    }

    for idx, file_info in enumerate(files):
        self.update_state(
            state="PROGRESS",
            meta={"current": idx + 1, "total": total, "file": file_info["filename"]}
        )

        prompt = (
            f"Review the following code file: `{file_info['filename']}`.\n"
            f"Analyze AST complexity, concurrency safety, edge cases, and security vulnerabilities.\n\n"
            f"```{file_info.get('code', '')}```"
        )

        payload = {
            "model": settings.DEFAULT_CODE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }

        try:
            with httpx.Client(timeout=180.0) as client:
                res = client.post(f"{settings.LITELLM_URL}/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    analysis = res.json()["choices"][0]["message"]["content"]
                    results.append({"filename": file_info["filename"], "review": analysis, "status": "success"})
                else:
                    results.append({"filename": file_info["filename"], "error": res.text, "status": "failed"})
        except Exception as ex:
            results.append({"filename": file_info["filename"], "error": str(ex), "status": "error"})

    return {"status": "COMPLETED", "files_analyzed": results}