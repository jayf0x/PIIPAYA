import type { EntityFilter } from "$lib/types/ui";

const ENTITY_FILTERS: EntityFilter[] = [
  {
    key: "person",
    label: "PERSON",
    entity: "PERSON",
    color: "#d2e3fc",
    textColor: "#174ea6",
    dataType: "person",
  },
  {
    key: "loc",
    label: "LOCATION",
    entity: "LOCATION",
    color: "#ceead6",
    textColor: "#0d652d",
    dataType: "loc",
  },
  {
    key: "email",
    label: "EMAIL",
    entity: "EMAIL_ADDRESS",
    color: "#feefc3",
    textColor: "#b06000",
    dataType: "email",
  },
  {
    key: "phone",
    label: "PHONE",
    entity: "PHONE_NUMBER",
    color: "#fce8e6",
    textColor: "#a50e0e",
    dataType: "phone",
  },
  {
    key: "org",
    label: "ORGANIZATION",
    entity: "ORGANIZATION",
    color: "#e1d8f0",
    textColor: "#5e2a96",
    dataType: "org",
  },
  {
    key: "date",
    label: "DATE",
    entity: "DATE_TIME",
    color: "#d1f0e8",
    textColor: "#1a7660",
    dataType: "date",
  },
  {
    key: "money",
    label: "MONEY",
    entity: "MONEY",
    color: "#f0e4d1",
    textColor: "#8c5c1e",
    dataType: "money",
  },
  {
    key: "url",
    label: "URL",
    entity: "URL",
    color: "#f0d1e6",
    textColor: "#9c2e7a",
    dataType: "url",
  },
  {
    key: "ip",
    label: "IP ADDRESS",
    entity: "IP_ADDRESS",
    color: "#d1e0f0",
    textColor: "#2e5e9c",
    dataType: "ip",
  },
  {
    key: "cc",
    label: "CREDIT CARD",
    entity: "CREDIT_CARD",
    color: "#f0d1d1",
    textColor: "#9c2e2e",
    dataType: "cc",
  },
];

const HIGHLIGHT_CLASS_BY_ENTITY = new Map<string, string>(
  ENTITY_FILTERS.map((row) => [row.entity, `hl-${row.dataType}`]),
);

export function entityFiltersCatalog() {
  return ENTITY_FILTERS;
}

export function entityTypesCatalog() {
  return ENTITY_FILTERS.map((row) => row.entity);
}

export function highlightClassForEntity(entityType: string | null) {
  if (!entityType) return "";
  return HIGHLIGHT_CLASS_BY_ENTITY.get(entityType.toUpperCase()) ?? "";
}
