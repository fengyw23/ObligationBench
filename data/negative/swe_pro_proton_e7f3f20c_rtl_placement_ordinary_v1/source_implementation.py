from pathlib import Path
p=Path('/app/packages/components/components/popper/utils.ts')
s=p.read_text()
s += "\nexport const getPhysicalPlacement = (placement: PopperPlacement, rtl: boolean): PopperPlacement => {\n    if (!rtl) return placement;\n    switch (placement) {\n        case 'top-start': return 'top-end';\n        case 'top-end': return 'top-start';\n        case 'bottom-start': return 'bottom-end';\n        case 'bottom-end': return 'bottom-start';\n        default: return placement;\n    }\n};\n"
p.write_text(s)
p=Path('/app/packages/components/components/popper/usePopper.ts')
s=p.read_text().replace('getClickRect, getFallbackPlacements','getClickRect, getFallbackPlacements, getPhysicalPlacement',1)
s=s.replace('            arrowOffset(),',"            arrowOffset(),\n            {\n                name: 'direction',\n                async fn({ platform, elements }) {\n                    return { data: { rtl: Boolean(await platform.isRTL?.(elements.floating)) } };\n                },\n            },",1)
s=s.replace("placement: hidden ? 'hidden' : placement,","placement: hidden ? 'hidden' : getPhysicalPlacement(placement, Boolean(middlewareData.direction?.rtl)),",1)
p.write_text(s)
print('Popper reports physical top/bottom alignment using the actual floating element direction')
