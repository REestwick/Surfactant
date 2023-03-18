from typing import List, Optional

from pluggy import HookspecMarker

from surfactant.sbomtypes import SBOM, Relationship, Software

hookspec = HookspecMarker("surfactant")


@hookspec(firstresult=True)
def identify_file_type(filepath: str) -> Optional[str]:
    """Determine the type of file located at filepath, and return a string identifying the type
    that will be passed to file extraction plugins. Return `None` to indicate that the type was
    unable to be determined.

    :param filepath: The path to the file to determine the type of.
    :returns: A string identifying the type of file, or None if the file type could not be recognized.
    """


@hookspec
def extract_file_info(sbom: SBOM, software: Software, filename: str, filetype: str) -> object:
    """Extracts information from the given file to add to the given software entry. Return an
    object to be included as part of the metadata field, and potentially used as part of
    selecting default values for other Software entry fields. Returning `None` will not add
    anything to the Software entry metadata.

    :param sbom: The SBOM that the software entry is part of. Can be used to add observations or analysis data.
    :param software: The software entry the gathered information will be added to.
    :param filename: The full path to the file to extract information from.
    :param filetype: File type information based on magic bytes.
    :returns: An object to be added to the metadata field for the software entry. May be `None` to add no metadata.
    """


@hookspec
def establish_relationships(
    sbom: SBOM, software: Software, metadata
) -> Optional[List[Relationship]]:
    """Called to add relationships to an SBOM after information has been gathered.

    The function will be called once for every metadata object in every software
    entry in the SBOM. Realistically, this means a plugin should not be trying to
    establish relationships for the entire SBOM before returning, just for the
    software/metadata object that has been passed to it.

    Returns a list of relationships to be added to the SBOM.

    :param sbom: The SBOM object that the Software is part of.
    :param sw: The Software entry that the metadata object is from.
    :param metadata: The metadata object to establish relationships based on.
    :returns: A list of relationships to add to the SBOM.
    """


@hookspec
def write_sbom(sbom: SBOM, outfile) -> None:
    """Writes the contents of the SBOM to the given output file.

    :param sbom: The SBOM to write to the output file.
    :param outfile: The output file handle to write the SBOM to.
    """