import pytest

from services.database import create_test_client


@pytest.fixture
def db_client(tmp_path):
    client = create_test_client(str(tmp_path / "test.db"))
    yield client
    client.close()


@pytest.fixture(scope="session", autouse=True)
def _close_cached_app_client_at_session_end():
    """El cliente de `get_client()` (cacheado por st.cache_resource y usado por
    cualquier prueba que arranque app.py con AppTest) abre un hilo en segundo
    plano que no es daemon. Si no se cierra explícitamente, el proceso de
    pytest se queda colgado al terminar aunque todas las pruebas hayan
    pasado, porque Python espera a que ese hilo termine.
    """
    yield
    try:
        from services.database import get_client
        get_client().close()
    except Exception:
        pass
