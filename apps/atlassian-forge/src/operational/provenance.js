export const TRANSFORMATION_VERSION = "os.1.0.0-normalize";
export const CONNECTOR_VERSION = "jira-jsm.1.0.0";
export const SCHEMA_VERSION = "os.1.0.0";

export function provenance(fields) {
  return {
    sourceSystem: fields.sourceSystem,
    sourceProject: fields.sourceProject ?? null,
    sourceEndpoint: fields.sourceEndpoint ?? null,
    extractionTimestamp: fields.extractionTimestamp ?? null,
    sourceRecordReference: fields.sourceRecordReference ?? null,
    transformationVersion: TRANSFORMATION_VERSION,
    evidenceClass: fields.evidenceClass,
    observationWindow: fields.observationWindow ?? null,
    derivationMethod: fields.derivationMethod ?? null,
    transportAuthenticity: fields.transportAuthenticity ?? "unknown",
  };
}
