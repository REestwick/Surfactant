# Copyright 2023 Lawrence Livermore National Security, LLC
# See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import uuid as uuid_module
from dataclasses import dataclass, field
from typing import List, Optional

from dataclasses_json import dataclass_json

from ._analysisdata import AnalysisData
from ._file import File
from ._hardware import Hardware
from ._observation import Observation
from ._provenance import SoftwareProvenance
from ._relationship import Relationship, StarRelationship
from ._software import Software, SoftwareComponent
from ._system import System


@dataclass_json
@dataclass
class SBOM:
    systems: List[System] = field(default_factory=list)
    hardware: List[Hardware] = field(default_factory=list)
    software: List[Software] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    analysisData: List[AnalysisData] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    starRelationships: List[StarRelationship] = field(default_factory=list)

    def add_relationship(self, rel: Relationship) -> None:
        self.relationships.append(rel)

    def create_relationship(self, xUUID: str, yUUID: str, relationship: str) -> Relationship:
        rel = Relationship(xUUID, yUUID, relationship)
        self.relationships.append(rel)
        return rel

    def find_relationship_object(self, relationship: Relationship) -> bool:
        return relationship in self.relationships

    def find_relationship(self, xUUID: str, yUUID: str, relationship: str) -> bool:
        return Relationship(xUUID, yUUID, relationship) in self.relationships

    def has_relationship(
        self, xUUID: str = None, yUUID: str = None, relationship: str = None
    ) -> bool:
        for rel in self.relationships:
            all_match = True
            if xUUID and rel.xUUID != xUUID:
                all_match = False
            if yUUID and rel.yUUID != yUUID:
                all_match = False
            if relationship and rel.relationship.upper() != relationship.upper():
                all_match = False
            if all_match:
                return True
        return False

    def find_software(self, sha256: Optional[str]) -> Optional[Software]:
        for sw in self.software:
            if sha256 == sw.sha256:
                return sw
        return None

    def add_software(self, sw: Software) -> None:
        self.software.append(sw)

    # pylint: disable=too-many-arguments
    def create_software(
        self,
        name: Optional[str] = None,
        size: Optional[int] = None,
        sha1: Optional[str] = None,
        sha256: Optional[str] = None,
        md5: Optional[str] = None,
        fileName: Optional[List[str]] = None,
        installPath: Optional[List[str]] = None,
        containerPath: Optional[List[str]] = None,
        captureTime: Optional[int] = None,
        version: Optional[str] = None,
        vendor: Optional[List[str]] = None,
        description: Optional[str] = None,
        relationshipAssertion: Optional[str] = None,
        comments: Optional[str] = None,
        metadata: Optional[List[object]] = None,
        supplementaryFiles: Optional[List[File]] = None,
        provenance: Optional[List[SoftwareProvenance]] = None,
        recordedInstitution: Optional[str] = None,
        components: Optional[List[SoftwareComponent]] = None,
    ) -> Software:
        sw = Software(
            name=name,
            size=size,
            sha1=sha1,
            sha256=sha256,
            md5=md5,
            fileName=fileName,
            installPath=installPath,
            containerPath=containerPath,
            captureTime=captureTime,
            version=version,
            vendor=vendor,
            description=description,
            relationshipAssertion=relationshipAssertion,
            comments=comments,
            metadata=metadata,
            supplementaryFiles=supplementaryFiles,
            provenance=provenance,
            recordedInstitution=recordedInstitution,
            components=components,
        )
        self.software.append(sw)
        return sw

    def merge(self, sbom_m: SBOM) -> SBOM:
        merged_sbom = SBOM()
        # merged/old to new UUID map
        uuid_updates = {}

        # merge systems entries
        if self.systems:
            for system in self.systems:
                # check for duplicate UUID/name, merge with existing entry
                if existing_system := self._find_systems_entry(
                    merged_sbom, uuid=system.UUID, name=system.name
                ):
                    # merge system entries
                    u1, u2 = existing_system.merge(system)
                    print(f"MERGE_DUPLICATE_SYS: uuid1={u1}, uuid2={u2}")
                    uuid_updates[u2] = u1
                else:
                    merged_sbom.systems.append(system)
        if sbom_m.systems:
            for system in sbom_m.systems:
                # check for duplicate UUID/name, merge with existing entry
                if existing_system := self._find_systems_entry(
                    merged_sbom, uuid=system.UUID, name=system.name
                ):
                    # merge system entries
                    u1, u2 = existing_system.merge(system)
                    print(f"MERGE_DUPLICATE_SYS: uuid1={u1}, uuid2={u2}")
                    uuid_updates[u2] = u1
                else:
                    merged_sbom.systems.append(system)

        # merge software entries
        if self.software:
            for sw in self.software:
                # check for a duplicate hash, and merge with the existing entry
                if existing_sw := self._find_software_entry(
                    merged_sbom, uuid=sw.UUID, sha256=sw.sha256, md5=sw.md5, sha1=sw.sha1
                ):
                    u1, u2 = existing_sw.merge(sw)
                    print(f"MERGE_DUPLICATE: uuid1={u1}, uuid2={u2}")
                    uuid_updates[u2] = u1
                else:
                    merged_sbom.software.append(sw)
        if sbom_m.software:
            for sw in sbom_m.software:
                # NOTE: Do we want to pass in teh UUID here? What if we have two different UUIDs for the same file? Should hashes be required?
                if existing_sw := self._find_software_entry(
                    merged_sbom, uuid=sw.UUID, sha256=sw.sha256, md5=sw.md5, sha1=sw.sha1
                ):
                    u1, u2 = existing_sw.merge(sw)
                    print(f"MERGE DUPLICATE: uuid1={u1}, uuid2={u2}")
                    uuid_updates[u2] = u1
                else:
                    merged_sbom.software.append(sw)

        # merge relationships
        if self.relationships:
            for rel in self.relationships:
                # rewrite UUIDs before doing the search
                if rel.xUUID in uuid_updates:
                    rel.xUUID = uuid_updates[rel.xUUID]
                if rel.yUUID in uuid_updates:
                    rel.yUUID = uuid_updates[rel.yUUID]
                if existing_rel := self._find_relationship_entry(
                    merged_sbom,
                    xUUID=rel.xUUID,
                    yUUID=rel.yUUID,
                    relationship=rel.relationship,
                ):
                    print("DUPLICATE RELATIONSHIP: {existing_rel}")
                else:
                    merged_sbom.relationships.append(rel)
        if sbom_m.relationships:
            for rel in sbom_m.relationships:
                # rewrite UUIDs before doing the search
                if rel.xUUID in uuid_updates:
                    rel.xUUID = uuid_updates[rel.xUUID]
                if rel.yUUID in uuid_updates:
                    rel.yUUID = uuid_updates[rel.yUUID]
                if existing_rel := self._find_relationship_entry(
                    merged_sbom,
                    xUUID=rel.xUUID,
                    yUUID=rel.yUUID,
                    relationship=rel.relationship,
                ):
                    print(f"DUPLICATE RELATIONSHIP: {existing_rel}")
                else:
                    merged_sbom.relationships.append(rel)

        # rewrite container path UUIDs using rewrite map/list
        for sw in merged_sbom.software:
            if sw.containerPath:
                for idx, path in enumerate(sw.containerPath):
                    u = path[:36]
                    # if container path starts with an invalid uuid4, sbom might not be valid
                    if self.is_valid_uuid4(u):
                        if u in uuid_updates:
                            updated_path = path.replace(u, uuid_updates[u], 1)
                            sw.containerPath[idx] = updated_path
                # remove duplicates
                sw.containerPath = [*set(sw.containerPath)]
        print(f"UUID UPDATES: {uuid_updates}")
        # merge analysisData
        if self.analysisData:
            for analysisData in self.analysisData:
                # checks for duplicates might be nice, but unlikely to encounter often as these are added manually
                merged_sbom.analysisData.append(analysisData)
        if sbom_m.analysisData:
            for analysisData in sbom_m.analysisData:
                merged_sbom.analysisData.append(analysisData)
        # merge observations
        if self.observations:
            for observation in self.observations:
                # checks for duplicates might be nice, but unlikely to encounter often as these are added manually
                merged_sbom.observations.append(observation)
        if sbom_m.observations:
            for observation in sbom_m.observations:
                merged_sbom.observations.append(observation)
        # merge starRelationships
        if self.starRelationships:
            for rel in self.starRelationships:
                # rewrite UUIDs before doing the search
                if rel.xUUID in uuid_updates:
                    rel.xUUID = uuid_updates[rel.xUUID]
                if rel.yUUID in uuid_updates:
                    rel.yUUID = uuid_updates[rel.yUUID]
                if existing_rel := self._find_star_relationship_entry(
                    merged_sbom,
                    xUUID=rel.xUUID,
                    yUUID=rel.yUUID,
                    relationship=rel.relationship,
                ):
                    print(f"DUPLICATE STAR RELATIONSHIP: {existing_rel}")
                else:
                    merged_sbom.starRelationships.append(rel)
        if sbom_m.starRelationships:
            for rel in self.starRelationships:
                # rewrite UUIDs before doing the search
                if rel.xUUID in uuid_updates:
                    rel.xUUID = uuid_updates[rel.xUUID]
                if rel.yUUID in uuid_updates:
                    rel.yUUID = uuid_updates[rel.yUUID]
                if existing_rel := self._find_star_relationship_entry(
                    merged_sbom,
                    xUUID=rel.xUUID,
                    yUUID=rel.yUUID,
                    relationship=rel.relationship,
                ):
                    print(f"DUPLICATE STAR RELATIONSHIP: {existing_rel}")
                else:
                    merged_sbom.starRelationships.append(rel)
        return merged_sbom

    def _find_systems_entry(self, sbom: SBOM, uuid: Optional[str] = None, name: Optional[str] = None) -> Optional[System]:
        """Merge helper function to find and return
        the matching system entry in the provided sbom.

        Args:
            sbom (SBOM): The sbom to search.
            uuid (Optional[str]): The uuid of the desired system entry.
            name (Optional[str]): The name of the desired system entry.
        
        Returns:
            Optional[System]: The system found that matches the given criteria, otherwise None.
        """
        for system in sbom.systems:
            all_match = True
            if uuid:
                if system.UUID != uuid:
                    all_match = False
            if name:
                if system.name != name:
                    all_match = False
            if all_match:
                return system
        return None

    def _find_software_entry(self, sbom: SBOM, uuid: Optional[str] = None, sha256: Optional[str] = None, md5: Optional[str] = None, sha1: Optional[str] = None) -> Optional[Software]:
        """Merge helper function to find and return
        the matching software entry in the provided sbom.

        Args:
            sbom (SBOM): The sbom to search.
            uuid (Optional[str]): The uuid of the desired software entry to match against if no hashes were provided.
            sha256 (Optional[str]): The sha256 of the desired software entry.
            md5 (Optional[str]): The md5 of the desired software entry.
            sha1 (Optional[str]): The sha1 of the desired software entry.
        
        Returns:
            Optional[Software]: The software entry found that matches the given criteria, otherwise None.
        """
        for sw in sbom.software:
            match = False
            # If we have hashes to check
            if sha256 or md5 or sha1:
                # Check if we have both sides of the comparison, then compare. At least one hash must match
                if sw.sha256 and sha256:
                    if sw.sha256 == sha256:
                        match = True
                if sw.md5 and md5:
                    if sw.md5 == md5:
                        match = True
                if sw.sha1 and sha1:
                    if sw.sha1 == sha1:
                        match = True
            # If no hashes to check, match by UUID
            else:
                if sw.UUID == uuid:
                    match = True
            if match:
                return sw
        return None

    def _find_relationship_entry(self, sbom, xUUID: Optional[str] = None, yUUID: Optional[str] = None, relationship: Optional[str] = None) -> Optional[Relationship]:
        """Merge helper function to find and return
        the matching relationship entry in the provided sbom.

        Args:
            sbom (SBOM): The sbom to search.
            xUUID (Optional[str]): The xUUID of the desired relationship entry.
            yUUID (Optional[str]): The yUUID of the desired relationship entry.
            relationship (Optional[str]): The relationship type of the desired relationship entry.
            
        Returns:
            Optional[Relationship]: The relationship entry found that matches the given criteria, otherwise None.
        """
        for rel in sbom.relationships:
            all_match = True
            if xUUID:
                if rel.xUUID != xUUID:
                    all_match = False
            if yUUID:
                if rel.yUUID != yUUID:
                    all_match = False
            if relationship:
                if rel.relationship != relationship:
                    all_match = False
            if all_match:
                return rel
        return None

    def _find_star_relationship_entry(self, sbom: SBOM, xUUID: Optional[str] = None, yUUID: Optional[str] = None, relationship: Optional[str] = None) -> Optional[StarRelationship]:
        """Merge helper function to find and return
        the matching star relationship entry in the provided sbom.

        Args:
            sbom (SBOM): The sbom to search.
            xUUID (Optional[str]): The xUUID of the desired relationship entry.
            yUUID (Optional[str]): The yUUID of the desired relationship entry.
            relationship (Optional[str]): The relationship type of the desired relationship entry.
        
        Returns:
            Optional[StarRelationship]: The star relationship found that matches the given criteria, otherwise None.
        """
        for rel in sbom.starRelationships:
            all_match = True
            if xUUID:
                if rel.xUUID != xUUID:
                    all_match = False
            if yUUID:
                if rel.yUUID != yUUID:
                    all_match = False
            if relationship:
                if rel.relationship != relationship:
                    all_match = False
            if all_match:
                return rel
        return None

    def is_valid_uuid4(self, u: str) -> bool:
        """Merge helper function to check if a uuid is valid.

        Args:
            u (str):  The UUID to check.
            
        Returns:
            bool: True if the UUID is valid, otherwise False.
        """
        try:
            u_test = uuid_module.UUID(u, version=4)
        except ValueError:
            return False
        return str(u_test) == u
