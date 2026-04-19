"""Entry point pour memoraeu-mcp installé via pip/uvx."""
import asyncio


def run():
    from memoraeu_mcp.main import main
    asyncio.run(main())


if __name__ == "__main__":
    run()
