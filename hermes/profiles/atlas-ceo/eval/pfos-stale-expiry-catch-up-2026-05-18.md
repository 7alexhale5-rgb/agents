# PFOS Stale Expiry Catch-Up Evidence - 2026-05-18

Status: production catch-up completed; scheduled prevention planned in PFOS.

## Source

- Preflight source packet: `atlas-atlas-ceo-1779090522791`
- Post-catch-up source packet: `atlas-atlas-ceo-1779090560251`
- Adopted decision: `clear_pending_approval_queue_before_new_surface_area`
- Route used: `/api/cron/agent-actions-expire`
- Policy: expire `inbox.%` and `calendar.%` proposed actions older than 96 hours
- Privacy: aggregate and id-only evidence; no private content fields included

## Catch-Up Summary

- Preflight stale inbox/calendar count: 264
- Final stale inbox/calendar count: 0
- Total actions expired: 264
- Provider executions: 0
- Rows with `executed_at` set: 0
- Paired `agent.action.expired` events: 264
- Final dry run: `scanned=0`, `expired=0`, `failed=0`
- Fresh `memory.*` proposals remained proposed and out of scope

| Batch | Expired | Proposed range | Action mix |
| --- | ---: | --- | --- |
| 1 | 100 | 2026-05-12T06:05:20Z to 2026-05-12T14:05:31Z | 31 archive, 15 follow-up, 10 calendar holds, 4 reply drafts, 38 unsubscribe drafts, 2 labels |
| 2 | 100 | 2026-05-12T15:05:17Z to 2026-05-13T12:05:12Z | 23 archive, 21 follow-up, 9 calendar holds, 4 reply drafts, 38 unsubscribe drafts, 5 labels |
| 3 | 64 | 2026-05-13T12:05:13Z to 2026-05-13T18:05:26Z | 22 archive, 7 follow-up, 4 calendar holds, 28 unsubscribe drafts, 3 labels |

## Verification

- Each batch was preceded by a production dry run using
  `dry_run=true&limit=100&max_age_hours=96`.
- Each mutation batch returned `failed=0`.
- Each expired row was verified as `status=expired` and `executed_at=null`.
- Each expired row had exactly one paired `agent.action.expired` event in the
  catch-up window.
- Each event had `execution_triggered=false`,
  `private_payload_redacted=true`, `decision_surface=pfos_stale_queue_expiry`,
  and `expiration_reason=stale_context_regenerate_if_needed`.
- The post-catch-up packet showed only the 3 fresh `memory.*` proposals from
  2026-05-18, confirming the inbox/calendar stale residue was cleared without
  touching current memory work.

## Event Ids

- `cffbf472-9ff0-4994-b724-f283a17ceffd`, `1a2a2dd3-b38a-4dbc-9af7-c17860a4c5cd`, `1d321816-080c-47a7-be3f-b6d845b0dac0`, `a01eab24-d8fe-457d-908c-c0e816adea37`, `c7bdd37e-0f55-487d-ad86-98c0b0f3210c`, `433b0e2a-4fa8-40f5-98b1-23b9a226c7ec`, `9614b077-b676-4c6a-b5c5-4cd16785c291`, `8dabd510-c26b-4c10-bd2b-6a20b502e488`
- `5e28e32e-0824-4449-a383-b6d7a4b7b0ae`, `d524d524-16d2-4a3a-bedf-b07a95f6180b`, `61ce57bb-641e-4fba-a582-37bb2c1ebb4f`, `c658b782-c5f1-4095-b15b-a7ac994b9651`, `d083ce23-0395-4551-91b3-f78cc574147a`, `dac7e0d2-9be9-4057-bca6-baa1437c715f`, `8666ec1b-0535-4933-8530-512fded021a2`, `637981a7-2304-4154-9e31-93b096abcae0`
- `bca8dc5b-3993-4040-b33d-ff5899f6c6f8`, `8566a33a-a889-459e-b620-dacb5bd65ecd`, `20ba6e2d-169b-4757-9eb1-cbf33b2c33de`, `2df184e2-24b3-4d6b-9219-33a996d852da`, `44e646e5-75df-407e-b198-17c19f0a0b74`, `e5779274-9d75-48e4-9f6a-f504f6d7695e`, `3fff65fa-3be7-4b3d-a501-50c1ccec0ad9`, `b1267d56-f24f-4c28-842c-fe18b582f670`
- `f5160cd1-80ef-4f95-b77c-4043468b14b9`, `5ffc9853-6b7f-4a96-b0ac-ae55c089d783`, `7d83a956-81d7-4d03-a3de-7804849c7e3e`, `ea8446d5-a266-4333-8579-0b92fd5d48e7`, `e20784df-6124-4a9a-9a77-9db0e80d540a`, `3c7a9f89-2637-446a-bd5c-dced7a567a3d`, `b16bbfb6-51cf-43f7-abf5-a3ed0a93196b`, `03e93de3-e618-472c-af78-521487d74dd2`
- `dd224b42-352b-433e-8e10-ed63c0798ca6`, `790a7096-bf2f-4b6a-bee4-227c05ef0d32`, `708a55de-6da0-420f-8e77-081d66d432bf`, `3539e70f-4f8b-448c-9738-fde7038ac02a`, `87be8949-88dd-4aa9-ab1a-8bfffc06d0fd`, `dfd6f297-8efb-40b3-9054-e2dc9885a9e6`, `cf2c2b63-81ab-4efb-b724-1246aa34e00d`, `0a13fe22-0608-487c-bc30-c4184a06a11c`
- `a2ad34be-22be-45c8-8634-48338e0ec489`, `83bf731a-8c64-4c78-9a2c-045a5fce207a`, `091e116b-13a9-4908-9774-3dec604c9226`, `97c6de4a-032c-4e3e-a90a-2c5903baf953`, `0dcb8125-110f-466f-bdfd-b6dc6bc68998`, `992c6b27-0e72-423d-a4ab-322b2db74d95`, `ba47d76e-4b33-485b-94c2-737e671d8fdb`, `3b4d37b1-a920-4f0d-bfbe-cfa528bba843`
- `f523b54d-f28b-403c-b50e-45f97cea35e0`, `1f3397fd-3f9b-4774-a15d-2f82163f611e`, `b56a6112-4900-444d-ac30-dbfa8585cf06`, `1caae119-dfcf-443d-9116-e5b373246f55`, `45bf7d44-e625-4cf9-b736-55059a77d285`, `d521075c-3095-4c29-820e-e307328123b6`, `c4283d73-54fc-45a7-a3e4-6a2db9f8be82`, `ae81aac1-4bf4-4ab1-8c5f-6d2462465ed0`
- `b9e31f98-8fdb-486f-b667-a8495d10bbb8`, `591f7c81-4bbb-4b95-baab-f7796b94f69c`, `8a6e5350-5f93-459f-9963-8dd628eebc90`, `4cdba8a8-f5a8-4070-8077-7841cfe172e9`, `7be6fdc1-6723-4fab-bd95-e0ecb38e4cf7`, `3cee6244-960a-4fea-8e77-b51565bca986`, `74d27597-3f7f-4df6-ac19-3ab640b42623`, `91ed7815-14ee-4d6e-85ec-77dedf87a157`
- `fd6aa03b-8575-4079-b34f-71615f614918`, `b72ffb0c-cf8a-42a9-b16d-3e04a0cdb680`, `4b17d46d-940f-4bd2-bb59-b84fef210369`, `709be48c-b0cd-43b5-a569-36b32bb9cca7`, `0dc64116-ee7c-4759-80c5-287cdf8e8faa`, `3c78f2a9-21f4-42ee-aa2b-128e9406700a`, `5d12cb7e-8f16-456e-b9ce-1319a99b0847`, `877e677e-2eb7-449b-9b7b-43842c482f42`
- `44d636a1-2df6-4ff5-9b40-ea04135cfd40`, `328e5d94-3a3d-4214-befc-221fcbe35b0c`, `442c69ba-d812-4d79-9109-9d00b977b046`, `2be061d9-2920-4551-bb00-e7de848f3446`, `af8079b8-e993-43c1-b4b2-670fd7a7774a`, `063f3b38-4fc5-46ef-ab4b-0a087b25fd65`, `a854cce7-1b1a-4b70-9137-333dab398bad`, `4b26d5af-1b02-4271-9372-c99831b299d4`
- `2eb7b085-1f12-43ba-bc5c-96c7c6aaac09`, `c12ed693-4e9c-4b4a-9483-fee635057253`, `9eec9854-6bf3-4fdf-a41c-c5d77440bce4`, `011a0381-d238-4f91-aba6-7e3c49c179c7`, `2194c048-b329-4c31-849e-c7d995cdcc77`, `0634f641-948f-4f2b-b900-b1723d713822`, `56646963-1f1b-4e6d-84ca-2b2fb61a6c12`, `e583b467-38dd-4096-af18-ee5bbb765a1c`
- `c6368706-2ef8-45e3-9d34-c9ba6e0689b6`, `7c88e40a-74ec-410c-a47f-56cebe9b1f44`, `aa62cad7-b2e6-4fe1-9385-ad1d1959dc8f`, `201cfd57-b611-44bb-84e6-ccc537f556ef`, `ac061725-022c-47cd-ba0d-276c7a07b7e8`, `171bc3bf-38b4-49f6-8a9c-72d984a87774`, `f9040cf4-3aa9-4b85-9a9c-4067ee8e6515`, `1b678625-7d29-4b70-b183-f1c7f4a2026e`
- `51093317-f26e-42ce-b72f-7d183d75b7ae`, `67650d57-84fd-4178-85bf-423528f439c0`, `0543239e-689a-439a-a91b-6c2db28adc14`, `dc9d6a3b-a967-4e11-936d-80706bdd5151`, `877cf818-c443-4552-9885-10d36283e885`, `04734654-c6d6-4b95-b4ef-78003b2ee83d`, `b3e8cecc-56ed-420e-9bcc-419b220bb81e`, `a5e47d97-497c-48b9-b311-9f8c5d4fbe03`
- `eefe0dc4-8931-4fb4-bc6e-4b786eede9a9`, `c145865d-9542-4d5d-a10b-a6edec83e229`, `3d1afb7a-b55d-4b78-af96-f7c79f11b1c5`, `8dba2e57-0824-45e1-af38-348e8eb1f593`, `65325d0b-eaa5-40b2-b854-a2839eddcd2d`, `7a54de37-7b81-489c-8737-02e43bf209fb`, `fc2f2a11-bcc8-4897-8f08-13a2520ba8bd`, `fcd1b9a2-65c2-4e11-aec5-da503231bff0`
- `c39b89fa-3111-4d99-884c-e8f3a0e70403`, `214a46f9-36bb-4d9b-a023-cc9e5cdd66e1`, `9cc13c15-052f-4167-a748-b4c280ba0176`, `ba0f71a3-3cf1-446c-bbba-bba6380ae6ce`, `6faab5b4-563f-4f33-95dd-1d97d1a2cadf`, `131e4d45-8676-4059-a45f-fb06105764d4`, `40365cb1-3849-4928-9477-66e168cf65e9`, `9ab7d9ad-884f-4270-a406-ae71da4ee28f`
- `fa703ba8-fbd4-4330-8c43-0b54fd96289b`, `70eca8af-28ee-4057-a66e-68dfc81e8180`, `b71fb05e-4f8c-4125-a2a9-45491f1b322f`, `f9c02716-eea1-41e0-8388-fb9d7ba1eb76`, `ada3c020-9ee2-4310-bd43-325073200a84`, `8cbf8750-2675-4ff8-8060-ba188a0e252f`, `f9990435-d301-4fb3-a991-b412ddd21da7`, `6c19eb80-4f2b-44c6-8e63-3e899b261ab8`
- `7469c09a-2624-4fac-b8d0-fa2d4f80a8bc`, `de6da1f4-cbae-471c-a7f2-1278aad4d231`, `7fc84f81-4b08-4817-b8a5-92fc0136df38`, `611144c8-cbc8-4171-af12-c6d4c0803409`, `99e9b438-8e3f-4386-93fb-3c8c2439ebf4`, `38f5efae-28bd-4d04-9024-26002f827243`, `32f05a94-6c5d-47ce-aec6-46e25ed373a7`, `0b9c47cd-2302-4d38-8048-9f5f8855b335`
- `d1d3df21-a7f0-4223-b175-0f75013aa1c2`, `edd667f7-d698-4787-8652-ee53de77dbd9`, `02eac629-03bd-443e-98ef-b7401caadf1b`, `b1c194cd-08ee-47bf-ae40-acfb32afdec8`, `d482f425-787f-4670-b9bf-91190ce5876c`, `48ca1e8b-487d-415e-a8ca-90612695fe65`, `6316940f-4e00-485e-b9c5-e3a87fe53a2b`, `c913fc58-857b-41e2-afa5-f8ded23236f4`
- `7094df82-a805-435e-9fbb-b41b571ff4ee`, `c4912b81-3ec7-4a84-90cb-17d61d745d7a`, `7ce7eb69-3bf6-43f5-aa37-a2ef531070a9`, `e2cfb8d8-e94b-465c-a892-8e21162a3692`, `4670ff6a-90e0-4806-a2fe-1440bfa7501b`, `3f0b05f7-c184-4b4e-9c2d-4b486bbca9ac`, `434144bd-c9ee-444e-a06b-734397590440`, `7e687034-27ae-4467-988e-31e9caabfe94`
- `5fd1aea4-e370-45af-8a18-92d875cea4c5`, `234f9b55-acda-4e91-b693-09c038fc0864`, `471f4f28-6676-452d-a6b1-46b9db595dca`, `86548db7-f27b-4023-b204-cc5aa6cd1cd2`, `dab921f0-04e6-4c32-9720-fd396b0c114d`, `3cef397f-7ebe-4a4b-9d32-2f344a4b3afe`, `5013f05a-22cf-45ab-85c9-ca046bb8b1fc`, `b85656d8-c26b-476e-9a5a-be48cf7dc6d7`
- `a0f43e57-2943-4f79-854a-4945504d13ba`, `de5a8ced-f237-46f0-a6e7-64053d574222`, `7648cfcc-aff1-4dce-b589-3b8834d0242c`, `e3a08d89-6d90-463c-a6f8-677cbbcbefba`, `e42b8143-182c-488e-993c-56bb755ad14e`, `cd82a3cf-46ff-4589-b082-66898b2b3565`, `0dd99834-91ea-4f2d-b8c2-f55aff64be84`, `a92f6ff4-900e-43a9-a484-deb61ba76c7b`
- `2dcd7c11-d90f-421f-9717-b58a9f86f343`, `8f1c8963-c72c-4f60-8448-99736bf1c1fa`, `df4f8480-11b6-4a13-9d6a-ad98e5b6af7c`, `1ae6f3a3-dc07-436d-8d0f-dacd9c6ca0c2`, `de088566-568c-4fcf-8883-e3e2e11b9563`, `e3f54184-d1e5-4c26-9687-d1c7597a0074`, `7faf57a9-cd23-4f81-a2d7-be438914f096`, `4b3c8645-572c-4d47-8fea-0c3e16ebf38d`
- `373b2f62-67fd-4d7b-bc9c-6ccd279d5e54`, `c96c94d4-6f2d-4f62-8dc0-c5317f31ae4b`, `686b4177-bad7-4413-bd19-fbf4a7660042`, `c1a43ed6-f771-48b7-9e2d-be75bd8dbb26`, `4b9b12c4-3f57-4541-af6b-5edf6a5107b2`, `fb8be767-c0f2-44a6-8142-36c3464ebb61`, `17f92842-d970-4923-a17d-631769d3c8d1`, `bdf2b44c-4cba-417e-a1ec-7b3947c72668`
- `a166fc53-943c-4f4b-84cb-acf1fc1a8483`, `0c321bec-7fb8-4886-9964-1279b2dbee0f`, `4327e732-939c-4248-b481-17331ba76254`, `165f724f-752e-42b8-89e2-cc40fb4b10b2`, `d6258b6b-3e1d-4982-98dc-d2d0ce6c86d5`, `df929c11-5981-4480-9053-aecf53e4af78`, `cfd1fcbf-2244-4724-a54d-651dc9658e46`, `e162ed46-dc3f-4e31-b945-fde4414345be`
- `10057ca4-6a65-41f1-bcc3-5cf11a185d0f`, `a1c2a01b-c739-48e2-891d-4a304b7a5871`, `d89c85f7-f93e-4669-aec7-fb44455c9f6a`, `eec0fc3d-14ce-4821-9aec-813760a843c8`, `1451bf0e-d254-4ec0-a7bc-07d166b993fc`, `170e1022-d72c-479c-8aa8-a040356778db`, `3c05c4f3-4f9a-4bc6-b972-d8ad104d38db`, `f8b623ef-f092-49b2-b664-5276cca341ed`
- `091ae34c-224c-4269-9e7a-5eb8057fb8ab`, `04164c2f-53d6-4414-a1c5-5e48eee39a83`, `8ba7e9d0-968b-4703-ab70-62e195889d18`, `0e0812b2-c7cc-4a0e-8a42-0141ac23001b`, `22c99031-05be-46e6-8d7f-5bad5867dec0`, `bc118f0b-2121-4d26-8f24-e11de4e010b4`, `d8f4f06e-fd0e-4dd2-9260-4d515a8064b4`, `417e22f4-a081-4aad-b3b9-8d879f025a8a`
- `dd98e1d9-54e2-40de-af14-82a39911b108`, `6f3fc420-98a0-4b91-8d02-92cacb431836`, `bbdab429-63b4-44b6-a4e4-ee83bf9587b5`, `94f5f518-f2a6-4971-9c27-8dd8b56a1db2`, `42be33ef-00e4-4ae1-9f80-55a427d61019`, `6ae019f4-b17b-4cb9-9dab-aaad68ef835c`, `28a858e4-dc0a-4ef4-89b2-07bf72456991`, `48af8238-0882-4cb3-a04b-6f9895964282`
- `504167d2-c84a-46fa-916e-4582dce0bb7c`, `1e785094-26d9-4843-b0cc-e938350b7871`, `745b86b9-5309-4ec0-8f81-f5acf6dde9d9`, `460cccec-e4fc-4b06-8a45-3c5d7da1a3b1`, `17527b85-f637-4a7b-aa47-8a84fcb9e018`, `e1693154-d684-4887-b72a-f7df91965edb`, `11f7fc6c-095b-43c3-a506-04e3705b623e`, `2ff9e934-8683-442f-8bea-0d280eb802e6`
- `60913cb7-1ff4-409a-9244-50645589cf3d`, `0b9dd3b4-9979-4b0b-bdc8-2adce23912eb`, `ca1651d4-e2a3-48bc-9297-df7e6df90c8e`, `3ca317c2-b037-47e1-9e23-c27caa26fcdc`, `85ff19e5-bf5c-41c0-87e4-17d2f5db458d`, `ddf0ae84-3af1-450a-a554-c19072ced764`, `1d71ed1d-2268-4a6e-a5ba-a11b1a77099d`, `21d8d298-314c-4267-9768-0884a7ff38ce`
- `e7b36896-40c1-4b83-93b4-be84bdfc2e39`, `b890295e-ac7e-4bd6-8dfc-d6e95b8baf44`, `15f54bda-9ceb-4626-ac08-879b94b99867`, `2cd8e4a2-be03-40e3-9296-b216400a5372`, `96fcfd4e-04da-4a00-b8ff-5589b687b2a6`, `47c8fc11-cc3d-4722-a28b-9755ecc937af`, `b6743f5a-1c1b-4c08-bf31-f40a6bf78c75`, `7269009b-86b1-40c5-be93-db99ace43e65`
- `5b157eb6-756f-4bd6-82c3-ee18eb894e9a`, `e57ae574-0bd7-43c9-9521-19e86b53d099`, `69e09d02-a8ec-4df0-9ffe-fb83fa29020a`, `580be4cc-f92a-4fbd-9259-f803c8bb0a20`, `13f4ec29-a7fa-411e-b673-7fa9f4134ea6`, `ffe285a9-4e5a-4787-85d6-db9c6dde559c`, `c21a063d-f2de-41ce-9134-7f2b2067116a`, `0f9582f9-6224-456c-b63d-81d03864c6f5`
- `04cd9554-1a08-419e-baeb-7e3c8cd6f44b`, `afa16439-8284-4193-b936-8ff7f7fce318`, `44a96380-5ac5-453b-8220-672c22f8e918`, `ec4ad054-229b-43a6-a837-290762f10da7`, `10c72a1e-9494-4e95-8c2a-ace919361e13`, `93add42d-b787-4f59-933a-09a3678587d2`, `834393c1-05a7-48cf-b09e-d34553c827fa`, `dfe8d269-a20b-4b4f-ad9c-5b1e71d63360`
- `318a55b1-261a-41d4-9373-1739163bd674`, `eb15a06b-a8ad-4c97-96f8-90103165ab5a`, `57fec1c4-23fe-42f1-b411-3f6c4deda8f0`, `2ae61772-f918-47ef-81b1-6adc45c59f73`, `d616b84a-2066-4293-8ceb-7ff984282bdd`, `864326a0-0164-44a6-8b46-48f1880f2e3f`, `53b46519-50c7-4027-9f8c-083720a23183`, `78132abe-e973-48c0-9cd2-313486e3bbdb`

## Next Regeneration Rule

Atlas should now treat stale inbox/calendar entries as expired context, not
operator work. Anything still real should be proposed again only after fresh
inbox/calendar state is read.
