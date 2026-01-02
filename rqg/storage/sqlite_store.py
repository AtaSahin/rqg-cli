import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from rqg.models import Run, RunMetadata, TestCaseResult, FailureCluster, FlakeScore
from rqg.config import PolicyConfig


class SQLiteStore:
    def __init__(self, db_path: str = ".rqg/rqg.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                repo TEXT,
                branch TEXT,
                commit_sha TEXT,
                ci_provider TEXT,
                workflow TEXT,
                job TEXT,
                build_number TEXT,
                attempt INTEGER,
                started_at TEXT,
                ended_at TEXT,
                os TEXT,
                browser TEXT,
                device TEXT,
                runner_pool TEXT,
                shard_id TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                test_id TEXT,
                suite TEXT,
                classname TEXT,
                name TEXT,
                duration_ms REAL,
                outcome TEXT,
                failure_text TEXT,
                fingerprint TEXT,
                retry_count INTEGER,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_clusters (
                fingerprint TEXT PRIMARY KEY,
                first_seen_at TEXT,
                last_seen_at TEXT,
                example_failure_text TEXT,
                infra_hints TEXT,
                test_ids TEXT,
                occurrence_count INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_commit ON runs(commit_sha);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_repo_branch ON runs(repo, branch);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_results_run ON test_results(run_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_results_test ON test_results(test_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_results_fingerprint ON test_results(fingerprint);
        """)
        
        conn.commit()
        conn.close()
    
    def save_run(self, run: Run):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        metadata = run.metadata
        cursor.execute("""
            INSERT OR REPLACE INTO runs (
                run_id, repo, branch, commit_sha, ci_provider, workflow, job,
                build_number, attempt, started_at, ended_at, os, browser,
                device, runner_pool, shard_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.run_id,
            metadata.repo,
            metadata.branch,
            metadata.commit_sha,
            metadata.ci_provider,
            metadata.workflow,
            metadata.job,
            metadata.build_number,
            metadata.attempt,
            metadata.started_at.isoformat() if metadata.started_at else None,
            metadata.ended_at.isoformat() if metadata.ended_at else None,
            metadata.os,
            metadata.browser,
            metadata.device,
            metadata.runner_pool,
            metadata.shard_id,
            "success" if all(tr.outcome == "pass" for tr in run.test_results) else "failure",
        ))
        
        cursor.execute("DELETE FROM test_results WHERE run_id = ?", (run.run_id,))
        
        for tr in run.test_results:
            cursor.execute("""
                INSERT INTO test_results (
                    run_id, test_id, suite, classname, name, duration_ms,
                    outcome, failure_text, fingerprint, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id,
                tr.test_id,
                tr.suite,
                tr.classname,
                tr.name,
                tr.duration_ms,
                tr.outcome,
                tr.failure_text[:10000] if tr.failure_text else None,
                tr.fingerprint,
                tr.retry_count,
            ))
        
        conn.commit()
        conn.close()
    
    def get_recent_runs(self, repo: str, branch: Optional[str] = None, 
                       lookback_runs: int = 50, lookback_days: int = 14) -> List[Run]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        
        query = """
            SELECT * FROM runs
            WHERE repo = ? AND started_at >= ?
        """
        params = [repo, cutoff_date]
        
        if branch:
            query += " AND branch = ?"
            params.append(branch)
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(lookback_runs)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        runs = []
        for row in rows:
            run_id = row["run_id"]
            metadata = RunMetadata(
                repo=row["repo"],
                branch=row["branch"],
                commit_sha=row["commit_sha"],
                ci_provider=row["ci_provider"],
                workflow=row["workflow"],
                job=row["job"],
                build_number=row["build_number"],
                attempt=row["attempt"],
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
                os=row["os"],
                browser=row["browser"],
                device=row["device"],
                runner_pool=row["runner_pool"],
                shard_id=row["shard_id"],
            )
            
            cursor.execute("SELECT * FROM test_results WHERE run_id = ?", (run_id,))
            test_rows = cursor.fetchall()
            
            test_results = []
            for tr_row in test_rows:
                test_results.append(TestCaseResult(
                    test_id=tr_row["test_id"],
                    suite=tr_row["suite"],
                    classname=tr_row["classname"],
                    name=tr_row["name"],
                    duration_ms=tr_row["duration_ms"],
                    outcome=tr_row["outcome"],
                    failure_text=tr_row["failure_text"],
                    fingerprint=tr_row["fingerprint"],
                    retry_count=tr_row["retry_count"],
                ))
            
            runs.append(Run(run_id=run_id, metadata=metadata, test_results=test_results))
        
        conn.close()
        return runs
    
    def get_failure_clusters(self, lookback_days: int = 14) -> List[FailureCluster]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        
        cursor.execute("""
            SELECT 
                tr.fingerprint,
                MIN(r.started_at) as first_seen,
                MAX(r.started_at) as last_seen,
                COUNT(DISTINCT tr.run_id) as occurrence_count
            FROM test_results tr
            JOIN runs r ON tr.run_id = r.run_id
            WHERE tr.fingerprint IS NOT NULL 
                AND tr.outcome = 'fail'
                AND r.started_at >= ?
            GROUP BY tr.fingerprint
        """, (cutoff_date,))
        
        rows = cursor.fetchall()
        
        clusters = []
        for row in rows:
            fingerprint = row["fingerprint"]
            
            cursor.execute("""
                SELECT example_failure_text, infra_hints, test_ids
                FROM failure_clusters
                WHERE fingerprint = ?
            """, (fingerprint,))
            
            cluster_row = cursor.fetchone()
            if cluster_row:
                example_text = cluster_row["example_failure_text"]
                infra_hints = json.loads(cluster_row["infra_hints"] or "[]")
                test_ids = json.loads(cluster_row["test_ids"] or "[]")
            else:
                cursor.execute("""
                    SELECT failure_text, test_id
                    FROM test_results
                    WHERE fingerprint = ? AND failure_text IS NOT NULL
                    LIMIT 1
                """, (fingerprint,))
                
                example_row = cursor.fetchone()
                example_text = example_row["failure_text"] if example_row else ""
                infra_hints = []
                test_ids = [example_row["test_id"]] if example_row else []
            
            clusters.append(FailureCluster(
                fingerprint=fingerprint,
                first_seen_at=datetime.fromisoformat(row["first_seen"]),
                last_seen_at=datetime.fromisoformat(row["last_seen"]),
                example_failure_text=example_text,
                infra_hints=infra_hints,
                test_ids=test_ids,
                occurrence_count=row["occurrence_count"],
            ))
        
        conn.close()
        return clusters
    
    def update_failure_cluster(self, cluster: FailureCluster):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO failure_clusters (
                fingerprint, first_seen_at, last_seen_at, example_failure_text,
                infra_hints, test_ids, occurrence_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cluster.fingerprint,
            cluster.first_seen_at.isoformat(),
            cluster.last_seen_at.isoformat(),
            cluster.example_failure_text[:5000],
            json.dumps(cluster.infra_hints),
            json.dumps(cluster.test_ids),
            cluster.occurrence_count,
        ))
        
        conn.commit()
        conn.close()

