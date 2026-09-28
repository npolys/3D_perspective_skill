"""The agent ontology's links to X3D must match x3d_mcp's node definitions.

X3D correctness itself (schema, DTD, ontology terms) is x3d_mcp's job. This repo checks its
own groundings in ontology/x3d_grounding.ttl against x3d_mcp's describe_node output,
snapshotted in contracts/x3d_defaults.json.
"""

import json
from pathlib import Path

import pytest

rdflib = pytest.importorskip("rdflib")
from rdflib import RDF, RDFS, Literal, Namespace, URIRef  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
X3D = Namespace("https://www.web3d.org/specifications/X3dOntology4.1#")
SC = Namespace("https://w3id.org/spatial-cognition#")
SNAPSHOT = json.loads((ROOT / "contracts" / "x3d_defaults.json").read_text(encoding="utf-8"))["nodes"]

# describe_node covers concrete nodes; abstract types are checked through a concrete node that inherits them.
CONCRETE = {"X3DViewpointNode": "Viewpoint", "X3DBindableNode": "Viewpoint"}
# Statements are not nodes, so describe_node does not cover them.
STATEMENTS = {"unit"}
NAVIGATION_TYPES = {"ANY", "WALK", "EXAMINE", "FLY", "LOOKAT", "NONE", "EXPLORE"}  # 23.4.4

GROUNDED_CONCEPTS = [
    "Agent", "BindingStack", "CoordinateFrame", "GravityModel", "GroundedPerspective",
    "LineOfSight", "Meter", "NavigationMode", "OccupancyConstraint", "PerceptualVolume",
    "PerspectiveProjection", "ReachableLocation", "SpatialRelationAssertion", "Transform",
    "TraversableSpace",
]


@pytest.fixture(scope="module")
def agent():
    graph = rdflib.Graph()
    for path in sorted((ROOT / "ontology").glob("*.ttl")):
        graph.parse(path, format="turtle")
    return graph


def groundings(agent):
    """(concept, node, field, grounding) for every :groundedIn annotation."""
    for concept, grounding in agent.subject_objects(SC.groundedIn):
        yield concept, agent.value(grounding, SC.x3dNode), agent.value(grounding, SC.x3dField), grounding


def local(term):
    return str(term).rsplit("#", 1)[-1]


def field_name(field):
    """X3D field name of an X3D Ontology field property: x3d:hasProxy -> proxy."""
    name = local(field)
    return name[3].lower() + name[4:] if name.startswith("has") and name[3:4].isupper() else name


def test_grounding_uses_x3d_4_1(agent):
    x3d_terms = {t for triple in agent for t in triple if isinstance(t, URIRef) and "X3dOntology" in str(t)}
    other_versions = [t for t in x3d_terms if not str(t).startswith(str(X3D).rstrip("#"))]
    assert x3d_terms and not other_versions


def test_grounded_fields_exist_in_describe_node(agent):
    bad = []
    for concept, node, field, _ in groundings(agent):
        name = local(node)
        if name in STATEMENTS:
            continue
        definition = SNAPSHOT.get(CONCRETE.get(name, name))
        if definition is None:
            bad.append(f"{local(concept)}: {name} is not in the describe_node snapshot")
        elif field is not None and field_name(field) not in definition["fields"]:
            bad.append(f"{local(concept)}: {name} has no field {field_name(field)}")
    assert not bad


def test_grounded_defaults_match_describe_node(agent):
    checked, bad = 0, []
    for _, node, field, grounding in groundings(agent):
        default = agent.value(grounding, SC.x3dDefault)
        if default is None:
            continue
        name = local(node)
        snapshot_default = SNAPSHOT[CONCRETE.get(name, name)]["fields"][field_name(field)]["default"]
        index = agent.value(grounding, SC.fieldIndex)
        actual = snapshot_default.split()[int(index)] if index is not None else " ".join(snapshot_default.split())
        checked += 1
        if actual != str(default):
            bad.append(f"{name}.{field_name(field)}: grounding {str(default)!r}, describe_node {actual!r}")
    assert not bad
    assert checked >= 20


def test_navigation_modes_are_the_x3d_navigation_types(agent):
    typed = {local(s).removeprefix("navigationType__") for s in agent.subjects(RDF.type, SC.NavigationMode)}
    assert typed == NAVIGATION_TYPES


@pytest.mark.parametrize("name", GROUNDED_CONCEPTS)
def test_concept_is_labelled_and_grounded(agent, name):
    concept = SC[name]
    assert agent.value(concept, RDFS.label) is not None
    assert agent.value(concept, RDFS.comment) is not None
    assert (concept, SC.groundedIn, None) in agent


def test_every_agent_term_is_labelled(agent):
    unlabelled = sorted(
        local(s) for s in set(agent.subjects(RDF.type, None))
        if isinstance(s, URIRef) and str(s).startswith(str(SC)) and agent.value(s, RDFS.label) is None
    )
    assert not unlabelled


def test_units_use_qudt(agent):
    units = {str(u) for u in agent.objects(None, SC.quantityUnit)}
    assert units and all(u.startswith("http://qudt.org/vocab/unit/") for u in units)
    exact_match = URIRef("http://www.w3.org/2004/02/skos/core#exactMatch")
    assert agent.value(SC.Meter, exact_match) == URIRef("http://qudt.org/vocab/unit/M")


def test_rules_are_plain_text(agent):
    assert all(isinstance(rule, Literal) for rule in agent.objects(None, SC.rule))
