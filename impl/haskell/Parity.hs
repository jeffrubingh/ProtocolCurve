-- | Parity checker for the canonical book format.
--
-- Reads @R|id|band|balance@ and @F|id|op|inputs|outputs@ lines, validates the
-- references, and prints the weighted depth with the FNV-1a 64 fingerprint
-- every other port must agree on.
module Main (main) where

import Data.Char (isSpace)
import Data.List (intercalate, sort)
import qualified Data.Map.Strict as Map
import qualified Data.Set as Set
import Data.Word (Word64)
import Numeric (showHex)
import System.Environment (getArgs)
import System.Exit (ExitCode (..), exitWith)
import Text.Printf (printf)

micro :: Integer
micro = 1000000

thinFloor :: Integer
thinFloor = 250 * micro

fnvOffset :: Word64
fnvOffset = 0xCBF29CE484222325

fnvPrime :: Word64
fnvPrime = 0x100000001B3

data Reserve = Reserve { reserveId :: String, reserveBand :: String, reserveBalance :: Integer }

data Flow = Flow { flowId :: String, flowOp :: String, flowInputs :: [String], flowOutputs :: [String] }

weightMicro :: String -> Integer
weightMicro band = case band of
  "buffer" -> 800000
  "edge" -> 450000
  "sink" -> 200000
  _ -> micro

normaliseBand :: String -> String
normaliseBand band
  | band `elem` ["seed", "core", "buffer", "edge", "sink"] = band
  | otherwise = "core"

splitList :: String -> [String]
splitList = filter (not . null) . splitOn ','

splitOn :: Char -> String -> [String]
splitOn separator text = case break (== separator) text of
  (head, []) -> [head]
  (head, _ : tail) -> head : splitOn separator tail

parse :: String -> Either String ([Reserve], [Flow])
parse text = go 1 (lines text) Map.empty Map.empty
  where
    go _ [] reserves flows = do
      mapM_ (checkReferences reserves) (Map.elems flows)
      Right (Map.elems reserves, Map.elems flows)
    go number (raw : rest) reserves flows
      | null line = go (number + 1) rest reserves flows
      | head line == '#' = go (number + 1) rest reserves flows
      | otherwise = case splitOn '|' line of
          ["R", rid, band, balance] ->
            if Map.member rid reserves
              then Left (at number ("duplicate reserve " ++ rid))
              else case reads balance of
                [(value, "")] -> go (number + 1) rest (Map.insert rid (Reserve rid (normaliseBand band) value) reserves) flows
                _ -> Left (at number "bad balance")
          ["F", fid, op, ins, outs] ->
            if Map.member fid flows
              then Left (at number ("duplicate flow " ++ fid))
              else case splitList outs of
                [] -> Left (at number ("flow " ++ fid ++ " credits nothing"))
                outputs ->
                  let flow = Flow fid (if null op then "derive" else op) (splitList ins) outputs
                   in go (number + 1) rest reserves (Map.insert fid flow flows)
          _ -> Left (at number "malformed record")
      where
        line = trim raw
    at number message = "line " ++ show number ++ ": " ++ message

trim :: String -> String
trim = dropWhile isSpace . reverse . dropWhile isSpace . reverse

checkReferences :: Map.Map String Reserve -> Flow -> Either String ()
checkReferences reserves flow =
  case filter (`Map.notMember` reserves) (flowInputs flow ++ flowOutputs flow) of
    [] -> Right ()
    (missing : _) -> Left ("flow " ++ flowId flow ++ ": unknown reserve " ++ missing)

fingerprint :: [Reserve] -> [Flow] -> String
fingerprint reserves flows = pad (showHex hash "")
  where
    payload =
      unlines $
        map (\r -> "R|" ++ reserveId r ++ "|" ++ reserveBand r ++ "|" ++ show (reserveBalance r)) (sortOnId reserves)
          ++ map renderFlow (sortOnId flows)
    renderFlow flow =
      "F|" ++ flowId flow ++ "|" ++ flowOp flow ++ "|"
        ++ intercalate "," (sort (flowInputs flow))
        ++ "|"
        ++ intercalate "," (sort (flowOutputs flow))
    hash = foldl step fnvOffset (map (fromIntegral . fromEnum) payload) :: Word64
    step acc byte = (acc `xor'` byte) * fnvPrime
    xor' a b = a `xorWord` b
    xorWord a b = a `xor64` b
    xor64 = xor
    pad value = replicate (16 - length value) '0' ++ value

sortOnId :: (a -> String) -> [a] -> [a]
sortOnId key = sortOn' key

sortOn' :: Ord b => (a -> b) -> [a] -> [a]
sortOn' key = map snd . sort . map (\item -> (key item, item))

main :: IO ()
main = do
  args <- getArgs
  case args of
    [] -> putStrLn "usage: parity <book.txt>" >> exitWith (ExitFailure 2)
    (path : _) -> do
      text <- readFile path
      case parse text of
        Left message -> putStrLn ("error: " ++ message) >> exitWith (ExitFailure 3)
        Right (reserves, flows) -> do
          let ordered = sortOnId reserveId reserves
              orderedFlows = sortOnId flowId flows
              raw = sum (map reserveBalance ordered)
              depth = sum [reserveBalance r * weightMicro (reserveBand r) `div` micro | r <- ordered]
              thin = length [r | r <- ordered, reserveBalance r > 0, reserveBalance r < thinFloor]
              debited = Set.fromList [out | f <- orderedFlows, not (null (flowInputs f)), out <- flowOutputs f]
              origins = [reserveId r | r <- ordered, not (Set.member (reserveId r) debited)]
              score = if raw > 0 then fromIntegral depth / fromIntegral raw :: Double else 0
          putStrLn ("reserves " ++ show (length ordered))
          putStrLn ("flows " ++ show (length orderedFlows))
          putStrLn ("raw " ++ show raw)
          putStrLn ("depth " ++ show depth)
          printf "score %.4f\n" score
          putStrLn ("thin " ++ show thin)
          putStrLn ("origins " ++ intercalate "," origins)
          putStrLn ("fingerprint " ++ fingerprint ordered orderedFlows)
