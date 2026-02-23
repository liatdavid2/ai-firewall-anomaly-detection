import numpy as np
from sklearn.ensemble import IsolationForest
import hashlib
from typing import List

class AnomalyModel:

    def __init__(self) -> None:
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.01,
            random_state=42
        )
        # Train on synthetic "normal" samples (prototype)
        data = np.random.rand(3000, 4)
        self.model.fit(data)

    @staticmethod
    def _ip_to_num(ip: str) -> float:
        h = hashlib.md5(ip.encode()).hexdigest()
        return int(h[:8], 16) / 1e9

    @staticmethod
    def _protocol_to_num(protocol: str) -> float:
        return 1.0 if protocol.upper() == "TCP" else 0.0

    def extract_features(self, conn) -> List[float]:
        return [
            self._ip_to_num(str(conn.source_ip)),
            self._ip_to_num(str(conn.destination_ip)),
            conn.destination_port / 65535.0,
            self._protocol_to_num(conn.protocol),
        ]

    def score(self, conn) -> float:
        features = self.extract_features(conn)
        raw = float(self.model.decision_function([features])[0])
        # Map to 0..1 (prototype normalization)
        anomaly = 1.0 - (raw + 0.5)
        return max(0.0, min(1.0, anomaly))

model = AnomalyModel()
