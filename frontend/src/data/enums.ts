// FILE: src/data/enums.ts
// PHOENIX PROTOCOL - ENUMS V1.0 (SUBSCRIPTION MATRIX)
// 1. CREATED: Centralized Enums for the new subscription model.
// 2. PURPOSE: Ensures type safety and consistency across the frontend.

export enum AccountType {
    SOLO = "SOLO",
    ORGANIZATION = "ORGANIZATION",
}

export enum SubscriptionTier {
    BASIC = "BASIC",
    PRO = "PRO",
}

export enum ProductPlan {
    SOLO_PLAN = "SOLO_PLAN",
    TEAM_PLAN = "TEAM_PLAN",
}