from app.core.anomaly import model

def score_connection(conn) -> float:
    return model.score(conn)
