"""
Repository for disaster operations, operational zones, relief resources, and recommendations.
"""

from typing import List, Dict, Any, Optional
from ..core.database import get_db

class DisasterRepository:
    """Encapsulates data access queries for disaster coordination domain."""

    @staticmethod
    def get_kpis() -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM disaster_reports;")
            total_reports = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS verified FROM disaster_reports WHERE verification_status = 'VERIFIED';")
            verified_reports = cursor.fetchone()["verified"]

            cursor.execute("SELECT COUNT(*) AS pending FROM recommendations WHERE status = 'PENDING';")
            pending_recommendations = cursor.fetchone()["pending"]

            cursor.execute("SELECT COUNT(*) AS approved FROM recommendations WHERE status = 'APPROVED';")
            approved_recommendations = cursor.fetchone()["approved"]

            cursor.execute("SELECT COUNT(*) AS anchored FROM recommendations WHERE blockchain_tx_hash IS NOT NULL AND blockchain_tx_hash != '';")
            blockchain_anchored = cursor.fetchone()["anchored"]

            cursor.execute("SELECT SUM(available_quantity) AS stock FROM resources;")
            row_stock = cursor.fetchone()
            available_resources = row_stock["stock"] or 0

            cursor.execute("SELECT SUM(population_affected) AS pop FROM locations;")
            row_pop = cursor.fetchone()
            affected_population = row_pop["pop"] or 0

            cursor.execute("SELECT COUNT(*) AS critical FROM locations WHERE severity = 'CRITICAL';")
            critical_zones = cursor.fetchone()["critical"]

            return {
                "total_reports": total_reports,
                "verified_reports": verified_reports,
                "pending_recommendations": pending_recommendations,
                "approved_recommendations": approved_recommendations,
                "blockchain_anchored_decisions": blockchain_anchored,
                "available_resources": available_resources,
                "affected_population": affected_population,
                "critical_zones": critical_zones
            }

    @staticmethod
    def get_locations() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM locations ORDER BY priority_score DESC;")
            return cursor.fetchall()

    @staticmethod
    def get_resources() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resources ORDER BY id ASC;")
            return cursor.fetchall()

    @staticmethod
    def get_reports(location: Optional[str] = None, severity: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM disaster_reports WHERE 1=1"
            params: List[Any] = []
            if location:
                query += " AND location = ?"
                params.append(location)
            if severity:
                query += " AND severity = ?"
                params.append(severity.upper())
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            return cursor.fetchall()

    @staticmethod
    def get_recommendations(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            if status_filter:
                cursor.execute("SELECT * FROM recommendations WHERE status = ? ORDER BY priority_score DESC;", (status_filter.upper(),))
            else:
                cursor.execute("SELECT * FROM recommendations ORDER BY id DESC;")
            return cursor.fetchall()

    @staticmethod
    def get_recommendation_by_id(rec_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recommendations WHERE recommendation_id = ?;", (rec_id,))
            return cursor.fetchone()

    @staticmethod
    def update_recommendation_approval(
        rec_id: str,
        approved_quantity: int,
        approver_name: str,
        approved_at: str,
        blockchain_tx_hash: str,
        block_number: int,
        approver_wallet: str
    ) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE recommendations
            SET status = 'APPROVED',
                approved_quantity = ?,
                approved_by_supervisor_1 = ?,
                approved_at = ?,
                blockchain_tx_hash = ?,
                block_number = ?,
                approver_wallet = ?
            WHERE recommendation_id = ?;
            """, (approved_quantity, approver_name, approved_at, blockchain_tx_hash, block_number, approver_wallet, rec_id))

    @staticmethod
    def get_audit_trail(limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?;", (limit,))
            return cursor.fetchall()
