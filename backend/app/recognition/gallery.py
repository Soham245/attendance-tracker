"""Embedding gallery: in-memory store with cosine-similarity search.

The gallery holds ``(student_id, embedding)`` pairs built during enrollment.
At runtime, a query embedding is compared against the full gallery via a
single matrix multiply — O(N) brute-force cosine similarity.

Performance at VisionAttend scale:
  - 100 students x 20 images = 2,000 embeddings
  - Each embedding: 512 x float32 = 2 KB
  - Gallery matrix: ~3 MB in memory
  - Search time: <1 ms on any modern CPU

Persistence uses NumPy ``.npz`` (compressed) — fast to load, compact on
disk, zero extra dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from app.core.logging import get_logger


logger = get_logger("attendai.gallery")


@dataclass(frozen=True)
class GalleryMatch:
    """Result of a gallery search."""

    student_id: int
    similarity: float       # cosine similarity [0, 1]
    gallery_index: int      # index in the gallery matrix (for debugging)


@dataclass
class GalleryEntry:
    """One embedding in the gallery."""

    student_id: int
    embedding: np.ndarray   # shape (512,), L2-normalized
    image_source: str       # filename it came from (for debugging)


class EmbeddingGallery:
    """In-memory embedding gallery with cosine-similarity search.

    Constructed from a list of ``GalleryEntry`` objects. Immutable after
    construction for thread safety — the recognition runtime reads the
    gallery from multiple iterations of the frame loop without locks.

    To update the gallery (add/remove students), build a new instance and
    promote it via the model registry.
    """

    def __init__(self, entries: List[GalleryEntry]) -> None:
        if not entries:
            self._matrix = np.zeros((0, 512), dtype=np.float32)
            self._ids: List[int] = []
            self._sources: List[str] = []
            return

        self._ids = [e.student_id for e in entries]
        self._sources = [e.image_source for e in entries]
        # Stack into (N, 512) matrix for vectorized search.
        self._matrix = np.stack(
            [e.embedding.astype(np.float32) for e in entries]
        )

    @property
    def size(self) -> int:
        """Number of embeddings in the gallery."""
        return len(self._ids)

    @property
    def student_ids(self) -> List[int]:
        """Unique student IDs represented in the gallery."""
        return sorted(set(self._ids))

    def embeddings_for(self, student_id: int) -> int:
        """Count of embeddings for a given student."""
        return sum(1 for sid in self._ids if sid == student_id)

    def search(
        self,
        query: np.ndarray,
        top_k: int = 1,
    ) -> Optional[GalleryMatch]:
        """Find the closest gallery embedding to *query*.

        Parameters
        ----------
        query : (512,) float32, L2-normalized
        top_k : ignored for now (always returns best match)

        Returns
        -------
        GalleryMatch or None if gallery is empty.
        """
        if self.size == 0:
            return None

        # Cosine similarity = dot product when both vectors are L2-normalized.
        similarities = self._matrix @ query.astype(np.float32)
        best_idx = int(np.argmax(similarities))
        best_sim = float(similarities[best_idx])

        return GalleryMatch(
            student_id=self._ids[best_idx],
            similarity=best_sim,
            gallery_index=best_idx,
        )

    def search_with_aggregation(
        self,
        query: np.ndarray,
    ) -> Optional[GalleryMatch]:
        """Search with per-student average similarity (more robust).

        Instead of returning the single closest embedding, this averages
        similarity across all embeddings per student and returns the
        student with the highest average. Reduces the impact of a single
        outlier enrollment image.
        """
        if self.size == 0:
            return None

        similarities = self._matrix @ query.astype(np.float32)

        # Aggregate per student.
        student_sims: Dict[int, List[float]] = {}
        for idx, sid in enumerate(self._ids):
            student_sims.setdefault(sid, []).append(float(similarities[idx]))

        best_sid = -1
        best_avg = -1.0
        best_idx = 0
        for sid, sims in student_sims.items():
            avg = sum(sims) / len(sims)
            if avg > best_avg:
                best_avg = avg
                best_sid = sid
                # Find the index of the best individual match for this student.
                best_idx = max(
                    (i for i, s in enumerate(self._ids) if s == sid),
                    key=lambda i: float(similarities[i]),
                )

        return GalleryMatch(
            student_id=best_sid,
            similarity=best_avg,
            gallery_index=best_idx,
        )

    # -- persistence ----------------------------------------------------------

    def save(self, path: Path) -> None:
        """Persist gallery to a ``.npz`` file."""
        np.savez_compressed(
            str(path),
            embeddings=self._matrix,
            ids=np.array(self._ids, dtype=np.int64),
            sources=np.array(self._sources, dtype=object),
        )
        logger.info(
            "Gallery saved: %d embeddings, %d students → %s",
            self.size, len(self.student_ids), path,
        )

    @classmethod
    def load(cls, path: Path) -> "EmbeddingGallery":
        """Load a gallery from a ``.npz`` file."""
        data = np.load(str(path), allow_pickle=True)
        matrix = data["embeddings"]
        ids = data["ids"].tolist()
        sources = data["sources"].tolist() if "sources" in data else [""] * len(ids)

        entries = [
            GalleryEntry(
                student_id=int(ids[i]),
                embedding=matrix[i],
                image_source=str(sources[i]),
            )
            for i in range(len(ids))
        ]
        gallery = cls(entries)
        logger.info(
            "Gallery loaded: %d embeddings, %d students ← %s",
            gallery.size, len(gallery.student_ids), path,
        )
        return gallery
