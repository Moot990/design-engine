"""Cloud-only live readiness: a tiny text call and balance checks, no images."""
from engine.common import EngineError, config
from engine.providers import gemini, image_account_ready


def main():
    settings = config()
    # Test the selected text/vision model BEFORE spending any image credits.
    result = gemini(settings, 'Return only this JSON object: {"ready": true}')
    if result != {"ready": True}:
        raise EngineError("Gemini live readiness response failed validation")
    image_account_ready(settings)
    print("Live provider checks succeeded: Gemini responded; earned-only image access verified. No images generated.")


if __name__ == "__main__":
    try:
        main()
    except EngineError as error:
        print("BLOCKED: " + str(error))
        raise SystemExit(2)
    except Exception:
        print("BLOCKED: unexpected provider check failure; sensitive details omitted")
        raise SystemExit(1)
